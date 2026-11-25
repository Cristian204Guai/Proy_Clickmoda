import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from '../api.config';
import { PaginatedResponse } from './catalog.service';
import { OrderResponse } from './checkout.service';

export type AdminOrderStatus = OrderResponse['estado'];

export interface AdminOrder extends OrderResponse {
  cliente_email: string;
}

export interface AdminOrderFilters {
  estado?: string;
  search?: string;
  page?: number;
}

@Injectable({ providedIn: 'root' })
export class AdminOrdersService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${API_URL}/admin/orders`;

  getOrders(filters: AdminOrderFilters = {}): Observable<PaginatedResponse<AdminOrder>> {
    let params = new HttpParams();

    if (filters.estado?.trim()) {
      params = params.set('estado', filters.estado.trim());
    }
    if (filters.search?.trim()) {
      params = params.set('search', filters.search.trim());
    }
    if (filters.page && filters.page > 1) {
      params = params.set('page', String(filters.page));
    }

    return this.http.get<PaginatedResponse<AdminOrder>>(`${this.baseUrl}/`, { params });
  }

  getOrder(id: number): Observable<AdminOrder> {
    return this.http.get<AdminOrder>(`${this.baseUrl}/${id}/`);
  }

  updateOrderStatus(id: number, estado: string): Observable<AdminOrder> {
    return this.http.patch<AdminOrder>(`${this.baseUrl}/${id}/`, { estado });
  }
}
