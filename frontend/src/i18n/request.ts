import { getRequestConfig } from "next-intl/server";
import { defaultLocale, isLocale } from "./config";

export default getRequestConfig(async ({ locale }) => {
  const nextLocale = locale && isLocale(locale) ? locale : defaultLocale;

  return {
    locale: nextLocale,
    messages: (await import(`../../messages/${nextLocale}.json`)).default,
  };
});
