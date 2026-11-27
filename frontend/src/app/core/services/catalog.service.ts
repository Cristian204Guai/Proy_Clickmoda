import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from '../api.config';

export type SizeOption = 'XS' | 'S' | 'M' | 'L' | 'XL';

export interface Category {
  id: number;
  nombre: string;
  slug: string;
  orden: number;
}

export interface ProductVariant {
  id: number;
  talla: SizeOption;
  color: string;
  color_hex: string;
  sku: string;
  stock: number;
}

export interface ProductImage {
  id: number;
  url: string;
  orden: number;
}

export interface Product {
  id: number;
  nombre: string;
  descripcion: string;
  categoria: number;
  categoria_nombre: string;
  categoria_slug: string;
  precio_base: string | number;
  porcentaje_iva: number;
  activo: boolean;
  creado_en: string;
  tallas_disponibles: SizeOption[];
  stock_total: number;
  variantes: ProductVariant[];
  imagenes: ProductImage[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface CatalogFilters {
  categories?: string[];
  size?: string;
  color?: string;
  min_price?: number | null;
  max_price?: number | null;
  search?: string;
  ordering?: string;
  page?: number;
}

@Injectable({ providedIn: 'root' })
export class CatalogService {
  private readonly http = inject(HttpClient);

  getCategories(): Observable<Category[]> {
    return this.http.get<Category[]>(`${API_URL}/categories/`);
  }

  getProducts(filters: CatalogFilters): Observable<PaginatedResponse<Product>> {
    let params = new HttpParams();

    if (filters.categories?.length) {
      params = params.set('category', filters.categories.join(','));
    }
    if (filters.size) {
      params = params.set('size', filters.size);
    }
    if (filters.color) {
      params = params.set('color', filters.color);
    }
    if (filters.min_price !== null && filters.min_price !== undefined && filters.min_price > 0) {
      params = params.set('min_price', String(filters.min_price));
    }
    if (filters.max_price !== null && filters.max_price !== undefined && filters.max_price > 0) {
      params = params.set('max_price', String(filters.max_price));
    }
    if (filters.search?.trim()) {
      params = params.set('search', filters.search.trim());
    }
    if (filters.ordering) {
      params = params.set('ordering', filters.ordering);
    }
    if (filters.page && filters.page > 1) {
      params = params.set('page', String(filters.page));
    }

    return this.http.get<PaginatedResponse<Product>>(`${API_URL}/products/`, { params });
  }

  getProductById(id: number): Observable<Product> {
    return this.http.get<Product>(`${API_URL}/products/${id}/`);
  }
}