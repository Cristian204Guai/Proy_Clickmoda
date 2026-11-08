import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, map, tap } from 'rxjs';
import { API_URL } from '../api.config';

export type Role = 'CLIENTE' | 'ADMIN';

export interface User {
  id: number;
  email: string;
  nombre: string;
  telefono: string;
  role: Role;
}
export interface LoginPayload { email: string; password: string; }
export interface RegisterPayload extends LoginPayload { nombre: string; telefono: string; }
interface LoginResponse { access: string; refresh: string; user: User; }
interface RefreshResponse { access: string; refresh?: string; }

const ACCESS = 'cm_access';
const REFRESH = 'cm_refresh';
const USER = 'cm_user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly base = `${API_URL}/auth`;

  private readonly _user = signal<User | null>(this.readUser());
  readonly user = this._user.asReadonly();
  readonly isLoggedIn = computed(() => this._user() !== null);
  readonly isAdmin = computed(() => this._user()?.role === 'ADMIN');

  get accessToken(): string | null { return localStorage.getItem(ACCESS); }
  get refreshToken(): string | null { return localStorage.getItem(REFRESH); }

  login(payload: LoginPayload): Observable<User> {
    return this.http.post<LoginResponse>(`${this.base}/login/`, payload).pipe(
      tap((r) => {
        localStorage.setItem(ACCESS, r.access);
        localStorage.setItem(REFRESH, r.refresh);
        this.setUser(r.user);
      }),
      map((r) => r.user),
    );
  }

  register(payload: RegisterPayload): Observable<User> {
    return this.http
      .post(`${this.base}/register/`, payload)
      .pipe(
        // tras registrarse, inicia sesión automáticamente
        (source) => new Observable<User>((sub) => {
          source.subscribe({
            next: () =>
              this.login({ email: payload.email, password: payload.password }).subscribe(sub),
            error: (e) => sub.error(e),
          });
        }),
      );
  }

  refresh(): Observable<string> {
    return this.http.post<RefreshResponse>(`${this.base}/refresh/`, { refresh: this.refreshToken }).pipe(
      tap((r) => {
        localStorage.setItem(ACCESS, r.access);
        if (r.refresh) localStorage.setItem(REFRESH, r.refresh); // el backend rota el refresh
      }),
      map((r) => r.access),
    );
  }

  /** Pide el perfil real al servidor (no confía en lo guardado en el navegador). */
  me(): Observable<User> {
    return this.http.get<User>(`${this.base}/me/`).pipe(tap((u) => this.setUser(u)));
  }

  logout(): void {
    const refresh = this.refreshToken;
    if (refresh) this.http.post(`${this.base}/logout/`, { refresh }).subscribe({ error: () => {} });
    this.clearSession();
  }

  clearSession(): void {
    [ACCESS, REFRESH, USER].forEach((k) => localStorage.removeItem(k));
    this._user.set(null);
  }

  private setUser(u: User): void {
    localStorage.setItem(USER, JSON.stringify(u));
    this._user.set(u);
  }

  private readUser(): User | null {
    try {
      const raw = localStorage.getItem(USER);
      return raw && localStorage.getItem(REFRESH) ? (JSON.parse(raw) as User) : null;
    } catch {
      return null;
    }
  }
}