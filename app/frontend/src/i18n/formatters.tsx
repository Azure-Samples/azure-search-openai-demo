export default {
  lowercase,
  uppercase,
  datetime,
  number,
  currency,
} as const;

export function lowercase(value: string) {
  return value.toLowerCase();
}

export function uppercase(value: string) {
  return value.toUpperCase();
}

/**
 * Returns the default qualified locale code
 * (language-REGION) for the given locale.
 *
 * @param lng The locale code.
 * @returns The qualified locale code, including region.
 */
function qualifiedLngFor(lng: string): string {
  switch (lng) {
    case "en":
      return "en-US";
    case "es":
        return "es-ES";
    case "fr":
      return "fr-FR";
    case "ja":
      return "ja-JP";
    default:
      return lng;
  }
}

/**
 * Formats a datetime.
 *
 * @param value - The datetime to format.
 * @param lng - The language to format the number in.
 * @param options - passed to Intl.DateTimeFormat.
 * @returns The formatted datetime.
 */
export function datetime(
  value: Date | number,
  lng: string | undefined,
  options?: Intl.DateTimeFormatOptions,
): string {
  return new Intl.DateTimeFormat(
    qualifiedLngFor(lng!),
    options,
  ).format(value);
}

/**
 * Formats a number.
 *
 * @param value - The number to format.
 * @param lng - The language to format the number in.
 * @param options - passed to Intl.NumberFormat.
 * @returns The formatted number.
 */
export function number(
  value: number,
  lng: string | undefined,
  options?: Intl.NumberFormatOptions,
): string {
  return new Intl.NumberFormat(
    qualifiedLngFor(lng!),
    options,
  ).format(value);
}

/**
 * Formats a number as currency.
 *
 * @param value - The number to format.
 * @param lng - The language to format the number in.
 * @param options - passed to Intl.NumberFormat.
 * @returns The formatted currency string.
 */
export function currency(
  value: number,
  lng: string | undefined,
  options?: Intl.NumberFormatOptions,
): string {
  return number(value, lng, {
    style: "currency",
    ...options,
  });
}
