/**
 * @file i18n/request.ts
 * @brief next-intl server-side message loader. Single-locale (en-US) for
 *        cutover; future locales register here.
 */
import { getRequestConfig } from "next-intl/server";
import messages from "./en-US.json";

export default getRequestConfig(async () => ({
  locale: "en-US",
  messages,
}));
