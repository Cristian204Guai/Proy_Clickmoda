import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { AuthService } from '../services/auth.service';

/** Protege /cuenta: exige sesión iniciada. */
export const authGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.isLoggedIn()
    ? true
    : router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
};

/** Protege /admin: confirma el rol con el servidor, no con lo guardado en el navegador. */
export const adminGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const toLogin = router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
  const toHome = router.createUrlTree(['/']);

  if (!auth.isLoggedIn()) return toLogin;
  return auth.me().pipe(
    map((u) => (u.role === 'ADMIN' ? true : toHome)),
    catchError(() => of(toLogin)),
  );
};