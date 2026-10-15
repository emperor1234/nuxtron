export type DraftEntity = { name: string; relationshipCount: number };
export type DraftRelationship = { from: string; type: string; to: string };

export type EntityGraphDraft = {
  entities: DraftEntity[];
  relationships: DraftRelationship[];
  duplicateEntityCount: number;
  duplicateRelationshipCount: number;
  linkedEntityCount: number;
  unlinkedEntities: string[];
  connectionCoveragePct: number;
};

function normalizeName(value: string): string {
  return value.trim().toLocaleLowerCase();
}

function csvCell(value: string): string {
  const safeValue = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value;
  return `"${safeValue.replace(/"/g, '""')}"`;
}

export function buildEntityGraphDraft(entityInput: string, relationshipInput: string): EntityGraphDraft {
  const entityLines = entityInput.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (entityLines.length === 0) throw new Error('Add at least one entity to create an outline.');
  if (entityLines.length > 100) throw new Error('Add up to 100 entity entries at a time.');

  const entities: DraftEntity[] = [];
  const byName = new Map<string, DraftEntity>();
  let duplicateEntityCount = 0;
  for (const name of entityLines) {
    if (name.length > 120) throw new Error('Keep each entity name to 120 characters or fewer.');
    if (name.includes('|')) throw new Error('Entity names cannot contain the pipe character used in relationship rows.');
    const key = normalizeName(name);
    if (byName.has(key)) {
      duplicateEntityCount += 1;
      continue;
    }
    const entity = { name, relationshipCount: 0 };
    entities.push(entity);
    byName.set(key, entity);
  }

  const relationshipLines = relationshipInput.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (relationshipLines.length > 200) throw new Error('Add up to 200 relationship entries at a time.');
  const relationships: DraftRelationship[] = [];
  const seenRelationships = new Set<string>();
  const linked = new Set<string>();
  let duplicateRelationshipCount = 0;

  for (const line of relationshipLines) {
    const parts = line.split('|').map((part) => part.trim());
    if (parts.length !== 3 || parts.some((part) => !part)) {
      throw new Error(`Use “source entity | relationship | target entity” for this row: ${line}`);
    }
    const [fromInput, type, toInput] = parts;
    const fromEntity = byName.get(normalizeName(fromInput));
    const toEntity = byName.get(normalizeName(toInput));
    if (!fromEntity || !toEntity) {
      throw new Error(`Relationship endpoints must match entities in your list: ${line}`);
    }
    if (fromEntity === toEntity) throw new Error(`An entity cannot relate to itself in this outline: ${line}`);
    if (type.length > 80) throw new Error('Keep relationship labels to 80 characters or fewer.');

    const relationKey = `${normalizeName(fromEntity.name)}|${normalizeName(type)}|${normalizeName(toEntity.name)}`;
    if (seenRelationships.has(relationKey)) {
      duplicateRelationshipCount += 1;
      continue;
    }
    seenRelationships.add(relationKey);
    relationships.push({ from: fromEntity.name, type, to: toEntity.name });
    fromEntity.relationshipCount += 1;
    toEntity.relationshipCount += 1;
    linked.add(normalizeName(fromEntity.name));
    linked.add(normalizeName(toEntity.name));
  }

  const unlinkedEntities = entities.filter((entity) => !linked.has(normalizeName(entity.name))).map((entity) => entity.name);
  const linkedEntityCount = entities.length - unlinkedEntities.length;
  return {
    entities,
    relationships,
    duplicateEntityCount,
    duplicateRelationshipCount,
    linkedEntityCount,
    unlinkedEntities,
    connectionCoveragePct: Math.round((linkedEntityCount / entities.length) * 100),
  };
}

export function entityGraphDraftCsv(draft: EntityGraphDraft): string {
  const header = ['Source entity', 'Relationship', 'Target entity'];
  const rows = draft.relationships.map(({ from, type, to }) => [from, type, to]);
  return [header, ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n');
}
