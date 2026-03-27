/** API client for Temshik marketplace backend */

export const API_BASE = import.meta.env.VITE_API_URL?.replace(/\/$/, '') || 'http://127.0.0.1:8000';

export function absoluteUrl(pathOrUrl: string): string {
  if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://')) return pathOrUrl;
  const base = API_BASE.replace(/\/$/, '');
  const p = pathOrUrl.startsWith('/') ? pathOrUrl : `/${pathOrUrl}`;
  return `${base}${p}`;
}

export function getToken(): string | null {
  return localStorage.getItem('access_token');
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem('access_token', token);
  else localStorage.removeItem('access_token');
}

async function request<T>(
  path: string,
  options: RequestInit & { token?: string | null } = {},
): Promise<T> {
  const token = options.token ?? getToken();
  const headers: HeadersInit = {
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const j = JSON.parse(text) as { detail?: unknown };
      detail = typeof j.detail === 'string' ? j.detail : text;
    } catch {
      /* keep text */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type CategoryPublic = {
  id: number;
  name: string;
  slug: string;
  listings_count: number;
};

export type ListingImage = { url: string; sort_order?: number };
export type ListingMine = {
  id: number;
  title: string | null;
  status: string;
  is_boosted: boolean;
  price: string | null;
  currency: string;
  category_id: number | null;
  city: string | null;
  images: ListingImage[];
};

export type Page<T> = {
  items: T[];
  meta: { page: number; page_size: number; total_items: number; total_pages: number };
};

export type PromotionRead = {
  id: number;
  listing_id: number;
  status: string;
  amount: string;
  currency: string;
};

export async function login(email: string, password: string) {
  const data = await request<{ access_token: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
    token: null,
  });
  setToken(data.access_token);
  return data;
}

export async function fetchCategories(token: string) {
  return request<CategoryPublic[]>('/categories', { token });
}

export async function fetchMyListings(
  token: string,
  params: {
    status?: string;
    category_id?: number | null;
    sort?: 'newest' | 'price_asc' | 'price_desc';
    page?: number;
  },
) {
  const sp = new URLSearchParams();
  if (params.status) sp.set('status', params.status);
  if (params.category_id != null && params.category_id > 0) sp.set('category_id', String(params.category_id));
  if (params.sort) sp.set('sort', params.sort);
  sp.set('page', String(params.page ?? 1));
  sp.set('page_size', '50');
  const q = sp.toString();
  return request<Page<ListingMine>>(`/listings/me?${q}`, { token });
}

export async function fetchPromotions(token: string, status?: string) {
  const sp = new URLSearchParams();
  sp.set('page', '1');
  sp.set('page_size', '50');
  if (status) sp.set('status', status);
  return request<Page<PromotionRead>>(`/promotions?${sp.toString()}`, { token });
}

export async function fetchListingPreview(token: string, listingId: number) {
  return request<ListingMine>(`/listings/${listingId}/preview`, { token });
}

export async function fetchMe(token: string) {
  return request<Record<string, unknown>>('/users/me', { token });
}
