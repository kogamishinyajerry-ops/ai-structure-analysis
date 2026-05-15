export interface ResultMeshNode {
  label: number;
  coordinates?: number[];
  deformed?: number[];
  displacement?: number[];
  partRoles?: string[];
}

export interface ResultMeshElement {
  label?: number;
  type?: string;
  connectivity?: number[];
  sourceElement?: number;
  partId?: number;
  partRole?: string;
  alive?: boolean;
  field?: string;
  value?: number;
}

export interface ResultMeshFrame {
  frame: number;
  timeMs: number;
  fieldLabel?: string;
  nodes: ResultMeshNode[];
  elements: ResultMeshElement[];
  fieldRanges?: ResultMeshFieldRanges;
}

export interface ResultMeshFieldRanges {
  valueMin?: number;
  valueMax?: number;
  maxDisplacement?: number;
  aliveElementCount?: number;
  deletedElementCount?: number;
}

export interface ResultMeshModelTreeNode {
  id?: string;
  label?: string;
  kind?: string;
  partId?: number;
  partRole?: string;
  elementCount?: number;
  aliveElementCount?: number;
  children?: ResultMeshModelTreeNode[];
}

export interface ResultMeshPayload {
  schemaVersion?: number;
  analysisType?: string;
  caseId?: string;
  fieldLabel?: string;
  fieldRanges?: ResultMeshFieldRanges;
  claimBoundary?: string;
  modelTree?: ResultMeshModelTreeNode;
  dynamicFrames?: ResultMeshFrame[];
  artifacts?: Record<string, unknown>;
}

export interface ResultMeshPlaybackSummary {
  frameCount: number;
  selectedFrameIndex: number;
  timeMs: number;
  nodeCount: number;
  elementCount: number;
  projectileElements: number;
  plateElements: number;
  aliveElements: number;
  deletedElements: number;
  fieldLabel: string;
  valueMin: number;
  valueMax: number;
  maxDisplacement: number;
  claimBoundary: string;
  modelTree: ResultMeshModelTreeNode[];
  selectedFrame: ResultMeshFrame | null;
}

const DEFAULT_FIELD_LABEL = 'Result field';
const DEFAULT_CLAIM_BOUNDARY =
  'Tier 1 engineering candidate; not signed validation; not benchmark agreement';

export function clampResultMeshFrameIndex(payload: unknown, requested: number): number {
  const frames = readFrames(payload);
  if (frames.length === 0 || !Number.isFinite(requested)) return 0;
  return Math.min(Math.max(Math.trunc(requested), 0), frames.length - 1);
}

export function summarizeResultMeshPlayback(
  payload: unknown,
  requestedFrameIndex: number,
): ResultMeshPlaybackSummary {
  const root = isRecord(payload) ? payload : {};
  const frames = readFrames(payload);
  const selectedFrameIndex = clampResultMeshFrameIndex(payload, requestedFrameIndex);
  const selectedFrame = frames[selectedFrameIndex] ?? null;
  const elements = selectedFrame?.elements ?? [];
  const ranges = readRanges(selectedFrame?.fieldRanges ?? root.fieldRanges);
  const valueRange = computeElementValueRange(elements);
  const modelTree = readModelTree(root.modelTree);

  return {
    frameCount: frames.length,
    selectedFrameIndex,
    timeMs: selectedFrame?.timeMs ?? 0,
    nodeCount: selectedFrame?.nodes.length ?? 0,
    elementCount: elements.length,
    projectileElements: elements.filter((element) => element.partRole === 'projectile').length,
    plateElements: elements.filter((element) => element.partRole === 'plate').length,
    aliveElements: elements.filter((element) => element.alive !== false).length,
    deletedElements: elements.filter((element) => element.alive === false).length,
    fieldLabel:
      asString(root.fieldLabel) ?? selectedFrame?.fieldLabel ?? DEFAULT_FIELD_LABEL,
    valueMin: ranges.valueMin ?? valueRange.valueMin ?? 0,
    valueMax: ranges.valueMax ?? valueRange.valueMax ?? 0,
    maxDisplacement: ranges.maxDisplacement ?? 0,
    claimBoundary: asString(root.claimBoundary) ?? DEFAULT_CLAIM_BOUNDARY,
    modelTree,
    selectedFrame,
  };
}

function readFrames(payload: unknown): ResultMeshFrame[] {
  if (!isRecord(payload)) return [];
  return asArray(payload.dynamicFrames).filter(isRecord).map(readFrame);
}

function readFrame(raw: Record<string, unknown>): ResultMeshFrame {
  return {
    frame: asNumber(raw.frame) ?? 0,
    timeMs: asNumber(raw.timeMs) ?? 0,
    fieldLabel: asString(raw.fieldLabel),
    nodes: asArray(raw.nodes).filter(isRecord).map(readNode),
    elements: asArray(raw.elements).filter(isRecord).map(readElement),
    fieldRanges: readRanges(raw.fieldRanges),
  };
}

function readNode(raw: Record<string, unknown>): ResultMeshNode {
  return {
    label: asNumber(raw.label) ?? 0,
    coordinates: readNumberList(raw.coordinates),
    deformed: readNumberList(raw.deformed),
    displacement: readNumberList(raw.displacement),
    partRoles: asArray(raw.partRoles).map(asString).filter(isString),
  };
}

function readElement(raw: Record<string, unknown>): ResultMeshElement {
  return {
    label: asNumber(raw.label),
    type: asString(raw.type),
    connectivity: readNumberList(raw.connectivity),
    sourceElement: asNumber(raw.sourceElement),
    partId: asNumber(raw.partId),
    partRole: asString(raw.partRole),
    alive: asBoolean(raw.alive),
    field: asString(raw.field),
    value: asNumber(raw.value),
  };
}

function readModelTree(value: unknown): ResultMeshModelTreeNode[] {
  if (!isRecord(value)) return [];
  return asArray(value.children).filter(isRecord).map(readModelTreeNode);
}

function readModelTreeNode(raw: Record<string, unknown>): ResultMeshModelTreeNode {
  return {
    id: asString(raw.id),
    label: asString(raw.label),
    kind: asString(raw.kind),
    partId: asNumber(raw.partId),
    partRole: asString(raw.partRole),
    elementCount: asNumber(raw.elementCount),
    aliveElementCount: asNumber(raw.aliveElementCount),
    children: asArray(raw.children).filter(isRecord).map(readModelTreeNode),
  };
}

function readRanges(value: unknown): ResultMeshFieldRanges {
  if (!isRecord(value)) return {};
  return {
    valueMin: asNumber(value.valueMin),
    valueMax: asNumber(value.valueMax),
    maxDisplacement: asNumber(value.maxDisplacement),
    aliveElementCount: asNumber(value.aliveElementCount),
    deletedElementCount: asNumber(value.deletedElementCount),
  };
}

function computeElementValueRange(elements: ResultMeshElement[]) {
  const values = elements.map((element) => element.value).filter(isFiniteNumber);
  if (values.length === 0) return {};
  return {
    valueMin: Math.min(...values),
    valueMax: Math.max(...values),
  };
}

function readNumberList(value: unknown): number[] | undefined {
  const values = asArray(value).map(asNumber).filter(isFiniteNumber);
  return values.length > 0 ? values : undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asString(value: unknown): string | undefined {
  return typeof value === 'string' && value.length > 0 ? value : undefined;
}

function isString(value: string | undefined): value is string {
  return typeof value === 'string';
}

function asBoolean(value: unknown): boolean | undefined {
  return typeof value === 'boolean' ? value : undefined;
}

function asNumber(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value !== 'string' || value.trim() === '') return undefined;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : undefined;
}

function isFiniteNumber(value: number | undefined): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}
