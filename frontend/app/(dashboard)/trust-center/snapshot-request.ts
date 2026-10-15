export type GovernancePolicySelection = {
  autonomy_enabled: boolean | null;
  allow_high_impact_actions: boolean | null;
  strict_policy_lock: boolean | null;
  policy_change_human_validation: boolean | null;
};

export type GovernanceSnapshotRequest = {
  autonomy_enabled: boolean;
  allow_high_impact_actions: boolean;
  strict_policy_lock: boolean;
  policy_change_human_validation: boolean;
  notes: string;
};

export function buildGovernanceSnapshotRequest(
  selection: GovernancePolicySelection,
  notes = '',
): GovernanceSnapshotRequest | null {
  const requiredKeys: (keyof GovernancePolicySelection)[] = [
    'autonomy_enabled',
    'allow_high_impact_actions',
    'strict_policy_lock',
    'policy_change_human_validation',
  ];
  if (requiredKeys.some((key) => typeof selection[key] !== 'boolean')) return null;

  return {
    autonomy_enabled: selection.autonomy_enabled as boolean,
    allow_high_impact_actions: selection.allow_high_impact_actions as boolean,
    strict_policy_lock: selection.strict_policy_lock as boolean,
    policy_change_human_validation: selection.policy_change_human_validation as boolean,
    notes: notes.trim(),
  };
}
