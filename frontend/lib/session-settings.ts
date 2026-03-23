/**
 * Session settings for the voice agent (archetype, difficulty, product).
 * Must match agent-starter-python session_settings.py.
 */
export interface SessionSettings {
  archetype: string;
  difficulty: string;
  product: string;
  training_scenario_id?: string;
  training_scenario_name?: string;
  prompt_blocks?: {
    client_role: string;
    archetype_description: string;
    scenario_description: string;
    language_and_format_instructions: string;
  };
}

export const DEFAULT_SESSION_SETTINGS: SessionSettings = {
  archetype: '',
  difficulty: '',
  product: '',
};
