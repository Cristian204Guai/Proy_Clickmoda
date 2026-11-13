import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from '../api.config';
import { CartService } from './cart.service';

export type PaymentMethod = 'TARJETA' | 'PSE' | 'NEQUI_DAVIPLATA' | 'CONTRA_ENTREGA';

export interface CreateOrderPayload {
  nombre_completo: string;
  telefono: string;
  direccion: string;
  ciudad: string;
  metodo_pago: PaymentMethod;
  token_pago: string;
  requiere_factura_electronica: boolean;
  tipo_documento?: string;
  numero_documento?: string;
  correo_factura?: string;
}

export interface OrderItemResponse {
  id: number;
  variante: number;
  nombre_producto: string;
  talla: string;
  color: string;
  cantidad: number;
  precio_unitario: number;
  porcentaje_iva: number;
  subtotal: number;
}

export interface OrderResponse {
  id: number;
  estado: string;
  metodo_pago: PaymentMethod;
  token_pago: string;
  subtotal: number;
  envio: number;
  impuestos: number;
  descuento: number;
  total: number;
  cupon_codigo: string;
  requiere_factura_electronica: boolean;
  tipo_documento: string;
  numero_documento: string;
  correo_factura: string;
  direccion_envio: {
    id: number;
    nombre_completo: string;
    telefono: string;
    direccion: string;
    ciudad: string;
  };
  items: OrderItemResponse[];
  creado_en: string;
}

@Injectable({ providedIn: 'root' })
export class CheckoutService {
  private readonly http = inject(HttpClient);
  private readonly cartService = inject(CartService);
  private readonly base = `${API_URL}/orders`;

  private get headers(): HttpHeaders {
    return new HttpHeaders({ 'X-Cart-Session': this.cartService.sessionKey });
  }

  /**
   * Simula la tokenización en la pasarela desde el navegador (RNF Seguridad / Pagos):
   * nunca almacena ni envía el número completo de tarjeta ni el CVV al backend.
   */
  tokenizeCardInMemory(cardNumber: string, installments: number): string {
    const digits = cardNumber.replace(/\D/g, '');
    const last4 = digits.slice(-4) || '0000';
    const randomToken = Math.random().toString(36).substring(2, 10);
    return `tok_sim_card_${last4}_${installments}c_${randomToken}`;
  }

  createOrder(payload: CreateOrderPayload): Observable<OrderResponse> {
    return this.http.post<OrderResponse>(`${this.base}/`, payload, {
      headers: this.headers,
    });
  }

  getOrderById(id: number): Observable<OrderResponse> {
    return this.http.get<OrderResponse>(`${this.base}/${id}/`, {
      headers: this.headers,
    });
  }
}