/** Fixed category labels (RU) and slug hints to match rows from GET /categories */

export type FixedCategory = {
  label: string;
  /** Prefer matching API category.slug (lowercase) */
  slugs: string[];
};

export const FIXED_CATEGORY_CHIPS: FixedCategory[] = [
  { label: 'Транспорт', slugs: ['transport', 'avto', 'cars'] },
  { label: 'Недвижимость', slugs: ['nedvizhimost', 'real-estate', 'property'] },
  { label: 'Дом и сад', slugs: ['dom-i-sad', 'home-garden', 'garden'] },
  { label: 'Услуги', slugs: ['uslugi', 'services'] },
  { label: 'Работа', slugs: ['rabota', 'jobs', 'work'] },
  { label: 'Личные вещи', slugs: ['lichnye-veschi', 'personal', 'clothes'] },
  { label: 'Животные', slugs: ['zhivotnye', 'animals', 'pets'] },
  { label: 'Детский мир', slugs: ['detskiy-mir', 'kids', 'children'] },
  { label: 'Спорт и хобби', slugs: ['sport-i-hobbi', 'sport', 'hobby'] },
  { label: 'Техника и электроника', slugs: ['tekhnika-i-elektronika', 'electronics', 'tech'] },
];

export function resolveCategoryIds(
  apiCategories: { id: number; slug: string }[],
): Map<string, number | null> {
  const bySlug = new Map(apiCategories.map((c) => [c.slug.toLowerCase(), c.id]));
  const m = new Map<string, number | null>();
  for (const fc of FIXED_CATEGORY_CHIPS) {
    let id: number | null = null;
    for (const s of fc.slugs) {
      const found = bySlug.get(s.toLowerCase());
      if (found != null) {
        id = found;
        break;
      }
    }
    m.set(fc.label, id);
  }
  return m;
}
