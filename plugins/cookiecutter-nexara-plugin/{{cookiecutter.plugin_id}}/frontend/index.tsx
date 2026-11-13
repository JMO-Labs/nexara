import { Example } from "./components/Example";

/** Register the plugin's UI slots with the Nexara frontend. */
export function registerPlugin(register: (slot: string, component: unknown) => void): void {
  register("{{cookiecutter.plugin_id}}.example", Example);
}
