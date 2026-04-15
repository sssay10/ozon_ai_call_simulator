/**
 * Session settings sent to LiveKit agent metadata.
 * prompt_blocks:
 * - persona_description: archetype/behavior of the client
 * - main_pain: key pain to reveal only after qualification state
 */
export interface SessionSettings {
  product: string;
  training_scenario_id?: string;
  training_scenario_name?: string;
  prompt_blocks?: {
    persona_description: string;
    main_pain: string;
  };
}

export const DEFAULT_SESSION_SETTINGS: SessionSettings = {
  product: '',
};
