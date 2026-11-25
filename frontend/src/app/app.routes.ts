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
    path: 'checkout',
    loadComponent: () => import('./features/checkout/checkout/checkout.component').then((m) => m.CheckoutComponent),
  },

  {
    path: 'factura/:id',
    loadComponent: () =>
      import('./features/invoices/invoice-detail/invoice-detail.component').then((m) => m.InvoiceDetailComponent),
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
    children: [
      {
        path: '',
        pathMatch: 'full',
        loadComponent: () =>
          import('./features/admin/dashboard/admin-dashboard.component').then(
            (m) => m.AdminDashboardComponent
          ),
      },
      {
        path: 'productos',
        loadComponent: () =>
          import('./features/admin/products/admin-products.component').then(
            (m) => m.AdminProductsComponent
          ),
      },
      {
        path: 'productos/nuevo',
        loadComponent: () =>
          import('./features/admin/product-form/admin-product-form.component').then(
            (m) => m.AdminProductFormComponent
          ),
      },
      {
        path: 'productos/:id/editar',
        loadComponent: () =>
          import('./features/admin/product-form/admin-product-form.component').then(
            (m) => m.AdminProductFormComponent
          ),
      },
      {
        path: 'categorias',
        loadComponent: () =>
          import('./features/admin/categories/admin-categories.component').then(
            (m) => m.AdminCategoriesComponent
          ),
      },
      {
        path: 'ordenes',
        loadComponent: () =>
          import('./features/admin/orders/admin-orders.component').then(
            (m) => m.AdminOrdersComponent
          ),
      },
      {
        path: 'usuarios',
        loadComponent: () =>
          import('./features/admin/users/admin-users.component').then(
            (m) => m.AdminUsersComponent
          ),
      },
      {
        path: 'facturacion',
        loadComponent: () =>
          import('./features/admin/invoices/admin-invoices.component').then(
            (m) => m.AdminInvoicesComponent
          ),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];