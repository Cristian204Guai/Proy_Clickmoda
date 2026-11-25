import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from '../api.config';
import { PaginatedResponse } from './catalog.service';
import { InvoiceDetail } from './invoice.service';

export type DianStepStatus = 'PENDIENTE' | 'LISTO' | 'APROBADA' | 'ERROR';

export interface AdminInvoiceSummary {
  id: number;
  numero: string;
  orden: number;
  fecha_emision: string;
  adquiriente_nombre: string;
  adquiriente_tipo_documento: string;
  adquiriente_documento: string;
  adquiriente_correo: string;
  base_gravable: number | string;
  iva: number | string;
  envio: number | string;
  total: number | string;
  estado: string;
  estado_respuesta: string;
  cufe: string;
  correos_enviados: number;
}

export interface AdminInvoicesFilters {
  search?: string;
  estado?: string;
  estado_respuesta?: '' | DianStepStatus;
  page?: number;
}

@Injectable({ providedIn: 'root' })
export class AdminInvoicesService {
  private readonly http = inject(HttpClient);
  private readonly base = `${API_URL}/admin/invoices`;

  getInvoices(
    filters: AdminInvoicesFilters = {}
  ): Observable<PaginatedResponse<AdminInvoiceSummary>> {
    let params = new HttpParams();

    if (filters.search?.trim()) {
      params = params.set('search', filters.search.trim());
    }
    if (filters.estado?.trim()) {
      params = params.set('estado', filters.estado.trim());
    }
    if (filters.estado_respuesta) {
      params = params.set('estado_respuesta', filters.estado_respuesta);
    }
    if (filters.page && filters.page > 1) {
      params = params.set('page', String(filters.page));
    }

    return this.http.get<PaginatedResponse<AdminInvoiceSummary>>(`${this.base}/`, { params });
  }

  getInvoiceDetail(id: number): Observable<InvoiceDetail> {
    return this.http.get<InvoiceDetail>(`${this.base}/${id}/`);
  }
}
