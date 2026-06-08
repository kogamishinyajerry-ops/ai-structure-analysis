import asyncio
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

# Reuse the hardened convergence SSOT (tools/calculix_driver, commit 41a2b22) rather than
# duplicating the positive-marker logic here — a downward (app -> tools) import per ADR-015.
from tools.calculix_driver import _check_convergence

logger = logging.getLogger(__name__)


class SolverJob:
    def __init__(self, job_id: str, case_name: str, work_dir: Path):
        self.job_id = job_id
        self.case_name = case_name
        self.work_dir = work_dir
        self.status = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.logs: list[str] = []
        self.process: asyncio.subprocess.Process | None = None
        self.queues: set[asyncio.Queue] = set()


class SolverService:
    """CalculiX 求解器管理服务"""

    def __init__(self):
        self.jobs: dict[str, SolverJob] = {}
        # 默认求解器可执行文件路径
        self.ccx_path = os.environ.get("CCX_PATH", "ccx")

    async def run_simulation(self, inp_file: Path) -> str:
        """启动仿真计算

        Args:
            inp_file: .inp 文件的绝对路径

        Returns:
            job_id: 任务唯一标识符
        """
        job_id = str(uuid.uuid4())
        case_name = inp_file.stem
        work_dir = inp_file.parent

        job = SolverJob(job_id, case_name, work_dir)
        self.jobs[job_id] = job

        # 异步启动进程
        asyncio.create_task(self._execute_solver(job, inp_file))

        return job_id

    async def _execute_solver(self, job: SolverJob, inp_file: Path):
        """执行求解器进程并记录日志"""
        job.status = "RUNNING"
        job.start_time = datetime.now()

        # CalculiX 命令: ccx [case_name] (不需要 .inp 后缀)
        cmd = [self.ccx_path, job.case_name]

        logger.info(f"Starting Solver Job {job.job_id}: {' '.join(cmd)} in {job.work_dir}")

        try:
            # 启动进程
            job.process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(job.work_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # 读取 stdout
            async def read_stream(stream):
                while True:
                    line = await stream.readline()
                    if line:
                        decoded_line = line.decode("utf-8", errors="ignore").strip()
                        job.logs.append(decoded_line)
                        # 实时推送到所有订阅队列
                        for q in list(job.queues):
                            await q.put(decoded_line)
                    else:
                        break

            await asyncio.gather(read_stream(job.process.stdout), read_stream(job.process.stderr))

            return_code = await job.process.wait()

            if return_code != 0:
                job.status = "FAILED"
                job.logs.append(f"Solver exited with code: {return_code}")
            elif not _check_convergence(job.work_dir, job.case_name):
                # rc==0 is NECESSARY but NOT SUFFICIENT: CalculiX exits 0 even when a step
                # fails to converge or cuts back to nothing. Require the same positive .sta
                # increment-row marker the driver SSOT uses before reporting COMPLETED —
                # otherwise a non-converged solve masquerades as a successful job to every
                # get_job_status consumer (candidate report, sensitivity sweep, copilot).
                job.status = "FAILED"
                job.logs.append(
                    "Solver exited 0 but no convergence marker in .sta; "
                    "treating as non-converged (not COMPLETED)."
                )
            else:
                job.status = "COMPLETED"

        except Exception as e:
            job.status = "FAILED"
            job.logs.append(f"System Error: {str(e)}")
            logger.error(f"Error running job {job.job_id}: {e}")

        finally:
            job.end_time = datetime.now()

    def get_job_status(self, job_id: str) -> dict | None:
        """查询任务状态"""
        job = self.jobs.get(job_id)
        if not job:
            return None

        return {
            "job_id": job.job_id,
            "status": job.status,
            "start_time": job.start_time.isoformat() if job.start_time else None,
            "end_time": job.end_time.isoformat() if job.end_time else None,
            "logs": job.logs[-50:],  # 返回最后50行日志
        }

    async def stop_job(self, job_id: str) -> bool:
        """停止正在运行的任务"""
        job = self.jobs.get(job_id)
        if not job or job.status != "RUNNING" or not job.process:
            return False

        try:
            logger.info(f"Stopping Job {job_id} (PID: {job.process.pid})")
            job.process.terminate()
            # 给 2 秒时间优雅关闭
            try:
                await asyncio.wait_for(job.process.wait(), timeout=2.0)
            except TimeoutError:
                logger.warning(f"Job {job_id} did not terminate, killing...")
                job.process.kill()

            job.status = "FAILED"
            job.logs.append("[SYSTEM] Job terminated by user.")
            return True
        except Exception as e:
            logger.error(f"Error stopping job {job_id}: {e}")
            return False


# 单例模式
_solver_service = None


def get_solver_service():
    global _solver_service
    if _solver_service is None:
        _solver_service = SolverService()
    return _solver_service
