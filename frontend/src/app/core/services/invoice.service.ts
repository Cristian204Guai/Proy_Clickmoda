import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from '../api.config';
import { CartService } from './cart.service';

export interface InvoiceLine {
  descripcion: string;
  cantidad: number;
  valor_unitario_sin_iva: number;
  porcentaje_iva: number;
  base_linea: number;
  iva_linea: number;
  total_linea: number;
}

export interface InvoiceResolution {
  id: number;
  numero_resolucion: string;
  prefijo: string;
  rango_desde: number;
  rango_hasta: number;
  fecha_desde: string;
  fecha_hasta: string;
  ambiente: string;
  rango_autorizado_texto: string;
}

export interface InvoiceDetail {
  id: number;
  orden: number;
  numero: string;
  prefijo: string;
  consecutivo: number;
  fecha_emision: string;
  emisor_nit: string;
  emisor_dv: string;
  emisor_razon_social: string;
  emisor_direccion: string;
  adquiriente_nombre: string;
  adquiriente_tipo_documento: string;
  adquiriente_documento: string;
  adquiriente_correo: string;
  adquiriente_consumidor_final: boolean;
  metodo_pago_label: string;
  subtotal_bruto: number;
  descuento: number;
  base_gravable: number;
  iva: number;
  envio: number;
  total: number;
  detalle_lineas: InvoiceLine[];
  cufe: string;
  qr_data: string;
  firma_digital: string;
  track_id: string;
  estado: string;
  estado_xml: 'PENDIENTE' | 'LISTO' | 'APROBADA' | 'ERROR';
  estado_firma: 'PENDIENTE' | 'LISTO' | 'APROBADA' | 'ERROR';
  estado_envio: 'PENDIENTE' | 'LISTO' | 'APROBADA' | 'ERROR';
  estado_respuesta: 'PENDIENTE' | 'LISTO' | 'APROBADA' | 'ERROR';
  codigo_respuesta_dian: string;
  mensaje_respuesta_dian: string;
  correos_enviados: number;
  ultimo_envio_correo: string | null;
  resolucion: InvoiceResolution;
}

export interface ResendInvoiceResponse {
  detail: string;
  correos_enviados: number;
  ultimo_envio_correo: string;
}

@Injectable({ providedIn: 'root' })
export class InvoiceService {
  private readonly http = inject(HttpClient);
  private readonly cartService = inject(CartService);
  private readonly base = `${API_URL}/invoices`;

  private get headers(): HttpHeaders {
    return new HttpHeaders({ 'X-Cart-Session': this.cartService.sessionKey });
  }

  getInvoice(id: number): Observable<InvoiceDetail> {
    return this.http.get<InvoiceDetail>(`${this.base}/${id}/`, { headers: this.headers });
  }

  downloadPdf(id: number): Observable<Blob> {
    return this.http.get(`${this.base}/${id}/pdf/`, {
      headers: this.headers,
      responseType: 'blob',
    });
  }

  downloadXml(id: number): Observable<Blob> {
    return this.http.get(`${this.base}/${id}/xml/`, {
      headers: this.headers,
      responseType: 'blob',
    });
  }

  resendEmail(id: number, correo?: string): Observable<ResendInvoiceResponse> {
    return this.http.post<ResendInvoiceResponse>(
      `${this.base}/${id}/resend/`,
      correo ? { correo } : {},
      { headers: this.headers }
    );
  }
}