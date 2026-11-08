import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-admin-layout',
  template: `
    <div style="display:flex;min-height:100vh">
      <aside style="width:14rem;background:#1F2937;color:#fff;padding:1rem">
        <strong>Click<span style="color:#F59E0B">Moda</span></strong>
        <nav aria-label="Administración">
          <ul style="list-style:none;padding:0">
            <li>Panel</li><li>Productos</li><li>Categorías</li>
            <li>Órdenes</li><li>Usuarios</li><li>Facturación DIAN</li>
          </ul>
        </nav>
        <button type="button" (click)="logout()">Cerrar sesión</button>
      </aside>
      <main style="flex:1;padding:1.5rem;background:#F9FAFB">
        <h1>Panel de administración</h1>
        <p>Sesión: {{ auth.user()?.email }} ({{ auth.user()?.role }})</p>
      </main>
    </div>
  `,
})
export class AdminLayoutComponent {
  readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  logout(): void {
    this.auth.logout();
    this.router.navigateByUrl('/login');
  }
}