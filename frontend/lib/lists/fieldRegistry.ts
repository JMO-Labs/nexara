/**
 * @file lib/lists/fieldRegistry.ts
 * @brief Singleton registry of list field types.
 */
import type { FieldType } from "./fieldTypes/base";
import { BoolField } from "./fieldTypes/BoolField";
import { TextField } from "./fieldTypes/TextField";
import { SelectField } from "./fieldTypes/SelectField";
import { MultiSelectField } from "./fieldTypes/MultiSelectField";
import { TimeField } from "./fieldTypes/TimeField";
import { CheckboxField } from "./fieldTypes/CheckboxField";
import { DateField } from "./fieldTypes/DateField";
import { LocationField } from "./fieldTypes/LocationField";
import { SignupField } from "./fieldTypes/SignupField";
import { UserPullField } from "./fieldTypes/UserPullField";

/** @brief Registry of field types keyed by FieldType.key. */
class FieldRegistry {
  private readonly types = new Map<string, FieldType>();

  /** @brief Add or replace a field type. */
  register(t: FieldType): void {
    this.types.set(t.key, t);
  }

  /** @brief Look up a type by key. */
  get(key: string): FieldType | undefined {
    return this.types.get(key);
  }

  /** @brief All registered keys. */
  keys(): string[] {
    return [...this.types.keys()];
  }
}

export const fieldRegistry = new FieldRegistry();
[
  BoolField,
  TextField,
  SelectField,
  MultiSelectField,
  TimeField,
  CheckboxField,
  DateField,
  LocationField,
  SignupField,
  UserPullField,
].forEach((t) => fieldRegistry.register(t));
