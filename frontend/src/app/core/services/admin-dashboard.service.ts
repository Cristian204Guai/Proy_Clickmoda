import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from '../api.config';

export interface AdminRecentOrder {
  id: number;
  cliente_nombre: string;
  estado: string;
  total: number;
  creado_en: string;
}

export interface AdminStats {
  total_productos: number;
  productos_activos: number;
  productos_agotados: number;
  ordenes_hoy: number;
  ventas_mes: number;
  total_usuarios: number;
  ordenes_recientes: AdminRecentOrder[];
}

@Injectable({ providedIn: 'root' })
export class AdminDashboardService {
  private readonly http = inject(HttpClient);
  private readonly base = `${API_URL}/admin/stats/`;

  getStats(): Observable<AdminStats> {
    return this.http.get<AdminStats>(this.base);
  }
}
