import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from '../api.config';
import { PaginatedResponse, SizeOption } from './catalog.service';

export interface AdminCategory {
  id: number;
  nombre: string;
  slug: string;
  orden: number;
  productos_count: number;
}

export interface AdminCategoryPayload {
  nombre: string;
  slug?: string;
  orden: number;
}

export interface AdminVariant {
  id?: number;
  talla: SizeOption;
  color: string;
  color_hex: string;
  sku?: string;
  stock: number;
}

export interface AdminProductImage {
  id?: number;
  url: string;
  orden: number;
  es_archivo?: boolean;
}

export type AdminProductEstado = 'Activo' | 'Agotado' | 'Inactivo';
export type AdminProductEstadoFilter = 'activo' | 'agotado' | 'inactivo' | '';

export interface AdminProduct {
  id: number;
  nombre: string;
  descripcion: string;
  categoria: number;
  categoria_nombre: string;
  categoria_slug: string;
  precio_base: string | number;
  porcentaje_iva: number;
  activo: boolean;
  estado_display: AdminProductEstado;
  stock_total: number;
  tallas_disponibles: SizeOption[];
  variantes: AdminVariant[];
  imagenes: AdminProductImage[];
  creado_en: string;
}

export interface AdminProductFilters {
  search?: string;
  category?: string | number;
  estado?: AdminProductEstadoFilter;
  page?: number;
}

export interface AdminProductPayload {
  nombre: string;
  descripcion: string;
  categoria: number;
  precio_base: number;
  porcentaje_iva: number;
  activo: boolean;
  variantes: AdminVariant[];
  imagenes?: AdminProductImage[];
}

export interface DeleteProductResponse {
  detail?: string;
  deactivated?: boolean;
}

@Injectable({ providedIn: 'root' })
export class AdminCatalogService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${API_URL}/admin`;

  getCategories(): Observable<AdminCategory[]> {
    return this.http.get<AdminCategory[]>(`${this.baseUrl}/categories/`);
  }

  createCategory(payload: AdminCategoryPayload): Observable<AdminCategory> {
    return this.http.post<AdminCategory>(`${this.baseUrl}/categories/`, payload);
  }

  updateCategory(id: number, payload: Partial<AdminCategoryPayload>): Observable<AdminCategory> {
    return this.http.patch<AdminCategory>(`${this.baseUrl}/categories/${id}/`, payload);
  }

  deleteCategory(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/categories/${id}/`);
  }

  getProducts(filters: AdminProductFilters = {}): Observable<PaginatedResponse<AdminProduct>> {
    let params = new HttpParams();

    if (filters.search?.trim()) {
      params = params.set('search', filters.search.trim());
    }
    if (filters.category !== undefined && filters.category !== null && String(filters.category).trim() !== '') {
      params = params.set('category', String(filters.category).trim());
    }
    if (filters.estado) {
      params = params.set('estado', filters.estado);
    }
    if (filters.page && filters.page > 1) {
      params = params.set('page', String(filters.page));
    }

    return this.http.get<PaginatedResponse<AdminProduct>>(`${this.baseUrl}/products/`, { params });
  }

  getProduct(id: number): Observable<AdminProduct> {
    return this.http.get<AdminProduct>(`${this.baseUrl}/products/${id}/`);
  }

  createProduct(payload: AdminProductPayload): Observable<AdminProduct> {
    return this.http.post<AdminProduct>(`${this.baseUrl}/products/`, payload);
  }

  updateProduct(id: number, payload: Partial<AdminProductPayload>): Observable<AdminProduct> {
    return this.http.patch<AdminProduct>(`${this.baseUrl}/products/${id}/`, payload);
  }

  deleteProduct(id: number): Observable<DeleteProductResponse | null> {
    return this.http.delete<DeleteProductResponse | null>(`${this.baseUrl}/products/${id}/`);
  }

  uploadProductImages(productId: number, files: File[]): Observable<AdminProductImage[]> {
    const formData = new FormData();
    for (const file of files) {
      formData.append('imagenes', file, file.name);
    }
    return this.http.post<AdminProductImage[]>(`${this.baseUrl}/products/${productId}/images/`, formData);
  }

  deleteProductImage(productId: number, imageId: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/products/${productId}/images/${imageId}/`);
  }
}
