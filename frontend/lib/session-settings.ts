/**
 * Session settings sent to LiveKit agent metadata (prompt blocks from DB only).
 */
export interface SessionSettings {
  product: string;
  training_scenario_id?: string;
  training_scenario_name?: string;
  prompt_blocks?: {
    persona_description: string;
    scenario_description: string;
  };
}

export const DEFAULT_SESSION_SETTINGS: SessionSettings = {
  product: '',
};
