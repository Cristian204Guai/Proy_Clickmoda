import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, finalize, shareReplay, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

let refreshing$: Observable<string> | null = null;

const withToken = (req: HttpRequest<unknown>, token: string) =>
  req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  const isAuthUrl = /\/auth\/(login|register|refresh)\/?$/.test(req.url);
  const token = auth.accessToken;
  const request = token && !isAuthUrl ? withToken(req, token) : req;

  return next(request).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status !== 401 || isAuthUrl || !auth.refreshToken) {
        return throwError(() => err);
      }
      // Una sola petición de refresco aunque fallen varias a la vez
      refreshing$ ??= auth.refresh().pipe(
        finalize(() => (refreshing$ = null)),
        shareReplay(1),
      );
      return refreshing$.pipe(
        catchError((e) => {
          auth.clearSession();
          router.navigate(['/login'], { queryParams: { returnUrl: router.url } });
          return throwError(() => e);
        }),
        switchMap((newToken) => next(withToken(req, newToken))),
      );
    }),
  );
};