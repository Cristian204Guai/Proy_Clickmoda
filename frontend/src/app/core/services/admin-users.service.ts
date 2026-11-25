import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from '../api.config';
import { PaginatedResponse } from './catalog.service';

export interface AdminUser {
  id: number;
  email: string;
  nombre: string;
  telefono: string;
  role: 'CLIENTE' | 'ADMIN';
  is_active: boolean;
  is_superuser: boolean;
  date_joined: string;
  ordenes_count: number;
}

export interface AdminUsersFilters {
  search?: string;
  role?: '' | 'CLIENTE' | 'ADMIN';
  is_active?: '' | 'true' | 'false';
  page?: number;
}

export interface AdminUserPatchPayload {
  is_active?: boolean;
  role?: 'CLIENTE' | 'ADMIN';
}

@Injectable({ providedIn: 'root' })
export class AdminUsersService {
  private readonly http = inject(HttpClient);
  private readonly base = `${API_URL}/admin/users`;

  getUsers(filters: AdminUsersFilters = {}): Observable<PaginatedResponse<AdminUser>> {
    let params = new HttpParams();

    if (filters.search?.trim()) {
      params = params.set('search', filters.search.trim());
    }
    if (filters.role) {
      params = params.set('role', filters.role);
    }
    if (filters.is_active) {
      params = params.set('is_active', filters.is_active);
    }
    if (filters.page && filters.page > 1) {
      params = params.set('page', String(filters.page));
    }

    return this.http.get<PaginatedResponse<AdminUser>>(`${this.base}/`, { params });
  }

  getUser(id: number): Observable<AdminUser> {
    return this.http.get<AdminUser>(`${this.base}/${id}/`);
  }

  updateUser(id: number, payload: AdminUserPatchPayload): Observable<AdminUser> {
    return this.http.patch<AdminUser>(`${this.base}/${id}/`, payload);
  }
}
