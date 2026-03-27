import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import {
  type CategoryPublic,
  type ListingMine,
  type PromotionRead,
  fetchCategories,
  fetchListingPreview,
  fetchMe,
  fetchMyListings,
  fetchPromotions,
  absoluteUrl,
  getToken,
  login,
  setToken,
} from './api';
import { FIXED_CATEGORY_CHIPS, resolveCategoryIds } from './categoryConfig';

type StatusTab = 'active' | 'draft' | 'inactive' | 'sold' | 'pending_payment';

const STATUS_TABS: { key: StatusTab; label: string }[] = [
  { key: 'active', label: 'Активные' },
  { key: 'draft', label: 'Черновики' },
  { key: 'pending_payment', label: 'Ожидают оплаты' },
  { key: 'inactive', label: 'Снятые' },
  { key: 'sold', label: 'Продано' },
];

const EMPTY_RU: Record<StatusTab, string> = {
  active: 'активных',
  draft: 'черновых',
  pending_payment: 'с ожидающей оплатой продвижения',
  inactive: 'снятых с публикации',
  sold: 'проданных',
};

const SORT_OPTIONS: { value: 'newest' | 'price_asc' | 'price_desc'; label: string }[] = [
  { value: 'newest', label: 'Сначала новые' },
  { value: 'price_asc', label: 'Сначала дешевле' },
  { value: 'price_desc', label: 'Сначала дороже' },
];

type PendingRow = { promotion: PromotionRead; listing: ListingMine | null };

export function MyListings({ token }: { token: string }) {
  const [categories, setCategories] = useState<CategoryPublic[]>([]);
  const [tab, setTab] = useState<StatusTab>('active');
  const [chipCategoryLabel, setChipCategoryLabel] = useState<string | null>(null);
  const [modalCategoryLabel, setModalCategoryLabel] = useState<string | null>(null);
  const [sort, setSort] = useState<'newest' | 'price_asc' | 'price_desc'>('newest');
  const [listings, setListings] = useState<ListingMine[]>([]);
  const [pendingRows, setPendingRows] = useState<PendingRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortOpen, setSortOpen] = useState(false);
  const [categoryOpen, setCategoryOpen] = useState(false);

  const labelToId = useMemo(() => {
    return resolveCategoryIds(categories.map((c) => ({ id: c.id, slug: c.slug })));
  }, [categories]);

  const effectiveCategoryId =
    (chipCategoryLabel && labelToId.get(chipCategoryLabel)) ?? null;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const c = await fetchCategories(token);
        if (!cancelled) setCategories(c);
      } catch {
        if (!cancelled) setCategories([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const loadListings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (tab === 'pending_payment') {
        const promPage = await fetchPromotions(token, 'pending_payment');
        const rows: PendingRow[] = await Promise.all(
          promPage.items.map(async (p) => {
            try {
              const listing = await fetchListingPreview(token, p.listing_id);
              return { promotion: p, listing };
            } catch {
              return { promotion: p, listing: null };
            }
          }),
        );
        setPendingRows(rows);
        setListings([]);
      } else {
        const page = await fetchMyListings(token, {
          status: tab,
          category_id: effectiveCategoryId && effectiveCategoryId > 0 ? effectiveCategoryId : null,
          sort,
        });
        setListings(page.items);
        setPendingRows([]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка загрузки');
      setListings([]);
      setPendingRows([]);
    } finally {
      setLoading(false);
    }
  }, [token, tab, effectiveCategoryId, sort]);

  useEffect(() => {
    loadListings();
  }, [loadListings]);

  const filteredPending = useMemo(() => {
    if (tab !== 'pending_payment') return [];
    if (!effectiveCategoryId) return pendingRows;
    return pendingRows.filter((r) => r.listing?.category_id === effectiveCategoryId);
  }, [tab, pendingRows, effectiveCategoryId]);

  const displayListings =
    tab === 'pending_payment'
      ? filteredPending.map((r) => r.listing).filter(Boolean) as ListingMine[]
      : listings;

  const sortedPendingForPromo =
    tab === 'pending_payment'
      ? [...filteredPending].sort((a, b) => {
          if (sort === 'price_asc') {
            const pa = a.listing?.price ? Number(a.listing.price) : Infinity;
            const pb = b.listing?.price ? Number(b.listing.price) : Infinity;
            return pa - pb;
          }
          if (sort === 'price_desc') {
            const pa = a.listing?.price ? Number(a.listing.price) : -Infinity;
            const pb = b.listing?.price ? Number(b.listing.price) : -Infinity;
            return pb - pa;
          }
          return (b.promotion.id || 0) - (a.promotion.id || 0);
        })
      : [];

  function onChipClick(label: string) {
    if (chipCategoryLabel === label) setChipCategoryLabel(null);
    else setChipCategoryLabel(label);
  }

  function applyModalCategory(label: string | null) {
    setModalCategoryLabel(label);
    setChipCategoryLabel(label);
    setCategoryOpen(false);
  }

  const categoryButtonText =
    chipCategoryLabel == null
      ? 'Категория: все'
      : `Категория: ${chipCategoryLabel}`;

  const sortButtonText = `Сортировать: ${SORT_OPTIONS.find((o) => o.value === sort)?.label ?? ''}`;

  const isEmpty =
    tab === 'pending_payment'
      ? sortedPendingForPromo.length === 0
      : displayListings.length === 0;

  return (
    <section className="ml ls-root">
      <h2 className="ml-title">Мои объявления</h2>

      <div className="ml-chips" role="list">
        <button
          type="button"
          className={`ml-chip ${chipCategoryLabel === null ? 'ml-chip--active' : ''}`}
          onClick={() => setChipCategoryLabel(null)}
        >
          Все
        </button>
        {FIXED_CATEGORY_CHIPS.map((c) => {
          const resolved = labelToId.get(c.label);
          const missing = resolved == null;
          return (
            <button
              key={c.label}
              type="button"
              disabled={missing}
              title={missing ? 'Нет совпадения в каталоге API — добавьте категорию с slug из categoryConfig' : ''}
              className={`ml-chip ${chipCategoryLabel === c.label ? 'ml-chip--active' : ''}`}
              onClick={() => onChipClick(c.label)}
            >
              {c.label}
            </button>
          );
        })}
      </div>

      <div className="ml-status-tabs" role="tablist">
        {STATUS_TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            className={`ml-tab ${tab === t.key ? 'ml-tab--active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="ml-filters">
        <button type="button" className="ml-filter-btn" onClick={() => setCategoryOpen(true)}>
          {categoryButtonText}
        </button>
        <button
          type="button"
          className="ml-filter-btn"
          onClick={() => setSortOpen(true)}
          disabled={tab === 'pending_payment'}
          title={tab === 'pending_payment' ? 'Сортировка для оплат упрощённая на клиенте' : ''}
        >
          {sortButtonText}
        </button>
      </div>

      {error && <p className="ml-error">{error}</p>}
      {loading && <p className="ml-muted">Загрузка…</p>}

      {!loading && isEmpty && (
        <div className="ml-empty">
          <h3>У вас нет {EMPTY_RU[tab]} объявлений</h3>
          <p>
            Разместите объявление на <strong>Temshik</strong> — так покупатели быстрее вас найдут.
          </p>
          <button type="button" className="ml-cta">
            Подать объявление
          </button>
        </div>
      )}

      {!loading && !isEmpty && tab !== 'pending_payment' && (
        <ul className="ml-cards">
          {displayListings.map((l) => (
            <li key={l.id} className="ml-card">
              {l.images[0] && (
                <img src={absoluteUrl(l.images[0].url)} alt="" className="ml-card-img" />
              )}
              <div className="ml-card-body">
                <div className="ml-card-top">
                  <span className="ml-card-title">{l.title || 'Без названия'}</span>
                  {l.is_boosted && <span className="ml-badge">Promote</span>}
                </div>
                <div className="ml-card-meta">
                  {l.price != null && (
                    <span>
                      {l.price} {l.currency}
                    </span>
                  )}
                  {l.city && <span>{l.city}</span>}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {!loading && !isEmpty && tab === 'pending_payment' && (
        <ul className="ml-cards">
          {sortedPendingForPromo.map(({ promotion: p, listing: l }) => (
            <li key={p.id} className="ml-card">
              {l?.images[0] && (
                <img src={absoluteUrl(l.images[0].url)} alt="" className="ml-card-img" />
              )}
              <div className="ml-card-body">
                <div className="ml-card-top">
                  <span className="ml-card-title">{l?.title || `Объявление #${p.listing_id}`}</span>
                  <span className="ml-badge ml-badge--warn">Ожидает оплаты</span>
                </div>
                <div className="ml-card-meta">
                  <span>
                    {p.amount} {p.currency}
                  </span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {sortOpen && (
        <ModalSheet title="Сортировка" onClose={() => setSortOpen(false)}>
          {SORT_OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              className={`ml-sheet-item ${sort === o.value ? 'ml-sheet-item--active' : ''}`}
              onClick={() => {
                setSort(o.value);
                setSortOpen(false);
              }}
            >
              {o.label}
            </button>
          ))}
        </ModalSheet>
      )}

      {categoryOpen && (
        <ModalSheet title="Категория" onClose={() => setCategoryOpen(false)}>
          <button type="button" className="ml-sheet-item" onClick={() => applyModalCategory(null)}>
            Все категории
          </button>
          <button
            type="button"
            className="ml-sheet-clear"
            onClick={() => applyModalCategory(null)}
          >
            Очистить фильтр
          </button>
          {FIXED_CATEGORY_CHIPS.map((c) => {
            const id = labelToId.get(c.label);
            const disabled = id == null;
            return (
              <button
                key={c.label}
                type="button"
                disabled={disabled}
                className={`ml-sheet-item ${modalCategoryLabel === c.label ? 'ml-sheet-item--active' : ''}`}
                onClick={() => applyModalCategory(c.label)}
              >
                {c.label}
              </button>
            );
          })}
        </ModalSheet>
      )}
    </section>
  );
}

function ModalSheet({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="ml-overlay" role="presentation" onClick={onClose}>
      <div
        className="ml-sheet"
        role="dialog"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="ml-sheet-head">
          <strong>{title}</strong>
          <button type="button" className="ml-sheet-close" onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </div>
        <div className="ml-sheet-body">{children}</div>
      </div>
    </div>
  );
}

export function ProfileShell() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState<string | null>(null);
  const [me, setMe] = useState<{ full_name?: string } | null>(null);
  const [tick, setTick] = useState(0);

  const activeToken = getToken();

  useEffect(() => {
    if (!activeToken) return;
    fetchMe(activeToken)
      .then((m) => setMe(m as { full_name?: string }))
      .catch(() => setMe(null));
  }, [activeToken, tick]);

  async function onLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoginError(null);
    try {
      await login(email, password);
      setTick((n) => n + 1);
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : 'Ошибка входа');
    }
  }

  function logout() {
    setToken(null);
    setMe(null);
    setTick((n) => n + 1);
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="logo">Temshik</span>
        <nav className="nav-icons" aria-label="Действия">
          <button type="button" className="icon-btn" title="Уведомления" aria-label="Уведомления">
            🔔
          </button>
          <button type="button" className="icon-btn" title="Настройки" aria-label="Настройки">
            ⚙
          </button>
        </nav>
      </header>

      <main className="app-main">
        {!activeToken ? (
          <form className="login-form" onSubmit={onLogin}>
            <h2>Вход</h2>
            <label>
              Email
              <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
            </label>
            <label>
              Пароль
              <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                required
              />
            </label>
            {loginError && <p className="ml-error">{loginError}</p>}
            <button type="submit">Войти</button>
          </form>
        ) : (
          <>
            <div className="profile-head">
              <div className="avatar-placeholder" aria-hidden />
              <div>
                <div className="profile-name">{me?.full_name || 'Пользователь'}</div>
                <button type="button" className="linkish" onClick={logout}>
                  Выйти
                </button>
              </div>
            </div>
            <MyListings token={activeToken} />
          </>
        )}
      </main>

      <footer className="bottom-nav" role="navigation">
        <span className="bottom-nav-item bottom-nav-item--active">Профиль</span>
        <span className="bottom-nav-item muted">Поиск</span>
        <span className="bottom-nav-item muted">Чаты</span>
      </footer>
    </div>
  );
}
