/**
 * Session settings sent to LiveKit agent metadata.
 * prompt_blocks: persona = who the client is; scenario_description = what the call is about (do not duplicate).
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
