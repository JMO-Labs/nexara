import { useExample } from "../hooks/useExample";

export function Example() {
  const { data } = useExample();
  return <p>{data?.message ?? "{{cookiecutter.plugin_name}}"}</p>;
}
