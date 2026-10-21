/**
 * The reading level label shown by the website and the Chrome extension.
 *
 * Both interfaces show the same measured result, so the wording is defined
 * once. When the measurement is not available, no label is shown at all.
 */

export interface ReadabilityLike {
  simplified?: {
    flesch_kincaid_grade?: number | null;
  } | null;
  target_grade_level?: number;
}

/**
 * Returns the reading level label, or null when it cannot be measured.
 *
 * A grade that is below the target is reported as such - the target is
 * never assumed to have been reached.
 */
export function formatReadingLevel(
  readability: ReadabilityLike | null | undefined,
  fallbackTarget = 5,
): string | null {
  const grade = readability?.simplified?.flesch_kincaid_grade;
  if (typeof grade !== 'number' || !Number.isFinite(grade)) return null;

  const target =
    typeof readability?.target_grade_level === 'number'
      ? readability.target_grade_level
      : fallbackTarget;

  if (grade < target) {
    return `Reading level: Below Grade ${target.toFixed(1)}`;
  }
  return `Reading level: Grade ${grade.toFixed(1)}`;
}
