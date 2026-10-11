export type DataSensitivity = "public" | "internal" | "customer" | "restricted";

export type PermissionActionId =
  | "read"
  | "draft"
  | "update"
  | "publish"
  | "destructive";

export type PermissionAction = {
  id: PermissionActionId;
  label: string;
  access: string;
  approval: string;
  audit: string;
};

export const PERMISSION_ACTIONS: readonly PermissionAction[] = [
  {
    id: "read",
    label: "Read approved records",
    access: "Read only, limited to the selected data scope and named purpose.",
    approval:
      "No per-action approval by default; log access. Restricted data needs policy review.",
    audit: "Agent identity, purpose, record scope, and access time.",
  },
  {
    id: "draft",
    label: "Draft content or responses",
    access:
      "Read access plus create-draft only; do not grant publish or send rights.",
    approval: "Review before any external publication or delivery.",
    audit: "Source context, draft version, reviewer, and final disposition.",
  },
  {
    id: "update",
    label: "Update selected records",
    access: "Write only approved fields on explicitly scoped records.",
    approval: "Require approval for each proposed change.",
    audit:
      "Target record, changed fields, before/after references, and approver.",
  },
  {
    id: "publish",
    label: "Publish or send externally",
    access: "Publish/send only to named channels, lists, or destinations.",
    approval: "Require explicit approval before each external action.",
    audit:
      "Destination, content/version reference, recipient scope, approver, and outcome.",
  },
  {
    id: "destructive",
    label: "Delete data or change access",
    access:
      "Not granted by default; use a separate, time-limited privileged workflow.",
    approval: "Block by default or require separate dual approval.",
    audit:
      "Reason, exact target, two approvers if enabled, and immutable outcome record.",
  },
];

export type PermissionMatrixInput = {
  agentName: string;
  dataSensitivity: DataSensitivity;
  actions: PermissionActionId[];
};

export type PermissionMatrixRow = {
  action: PermissionActionId;
  label: string;
  principal: string;
  dataScope: string;
  access: string;
  approval: string;
  audit: string;
};

export function buildPermissionMatrix(
  input: PermissionMatrixInput,
): PermissionMatrixRow[] {
  const selected = new Set(input.actions);
  const principal = input.agentName.trim() || "Unnamed agent";

  return PERMISSION_ACTIONS.filter((action) => selected.has(action.id)).map(
    (action) => {
      const scope = `${input.dataSensitivity} data; restrict to named records, fields, and purpose`;
      const approval =
        input.dataSensitivity === "restricted" && action.id === "read"
          ? "Require policy-owner review before granting; record each access."
          : action.approval;

      return {
        action: action.id,
        label: action.label,
        principal,
        dataScope: scope,
        access: action.access,
        approval,
        audit: action.audit,
      };
    },
  );
}
