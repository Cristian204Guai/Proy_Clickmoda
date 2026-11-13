import { Routes } from '@angular/router';
import { adminGuard, authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () => import('./features/catalog/catalog/catalog.component').then((m) => m.CatalogComponent),
  },

  {
    path: 'carrito',
    loadComponent: () =>

      import('./features/cart/cart/cart.component').then((m) => m.CartComponent),
  },



  {
    path: 'login',
    loadComponent: () => import('./features/auth/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'registro',
    loadComponent: () => import('./features/auth/register/register.component').then((m) => m.RegisterComponent),
  },
  {
    path: 'cuenta',
    canActivate: [authGuard],
    loadComponent: () => import('./features/account/account/account.component').then((m) => m.AccountComponent),
  },
  {
    path: 'admin',
    canActivate: [adminGuard],
    loadComponent: () => import('./features/admin/admin-layout/admin-layout.component').then((m) => m.AdminLayoutComponent),
  },
  { path: '**', redirectTo: '' },
];