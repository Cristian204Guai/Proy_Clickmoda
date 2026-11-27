import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { catchError, of } from 'rxjs';
import {
  AdminUser,
  AdminUsersService,
} from '../../../core/services/admin-users.service';
import { AuthService, User } from '../../../core/services/auth.service';

@Component({
  selector: 'app-admin-users',
  imports: [DatePipe, ReactiveFormsModule],
  templateUrl: './admin-users.component.html',
  styleUrls: ['./admin-users.component.css'],
})
export class AdminUsersComponent implements OnInit {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly usersService = inject(AdminUsersService);
  readonly auth = inject(AuthService);

  readonly filterForm = this.fb.group({
    search: [''],
    role: ['' as '' | 'CLIENTE' | 'ADMIN'],
    is_active: ['' as '' | 'true' | 'false'],
  });

  readonly users = signal<AdminUser[]>([]);
  readonly totalCount = signal(0);
  readonly currentPage = signal(1);
  readonly pageSize = 8;

  readonly loading = signal(true);
  readonly updatingUserId = signal<number | null>(null);
  readonly error = signal<string | null>(null);
  readonly actionError = signal<string | null>(null);
  readonly actionMessage = signal<string | null>(null);
  private readonly fetchedSelfSuperuser = signal<boolean | null>(null);

  readonly totalPages = computed(() =>
    Math.max(1, Math.ceil(this.totalCount() / this.pageSize))
  );

  readonly pageNumbers = computed(() =>
    Array.from({ length: this.totalPages() }, (_, idx) => idx + 1)
  );

  readonly currentIsSuperuser = computed(() => {
    const authUser = this.auth.user() as (User & { is_superuser?: boolean }) | null;
    if (!authUser) return false;
    if (typeof authUser.is_superuser === 'boolean') return authUser.is_superuser;
    const fetched = this.fetchedSelfSuperuser();
    if (fetched !== null) return fetched;
    const selfInList = this.users().find((u) => u.id === authUser.id);
    return selfInList?.is_superuser ?? false;
  });

  ngOnInit(): void {
    this.resolveSelfSuperuser();
    this.loadUsers();
  }

  applyFilters(): void {
    this.currentPage.set(1);
    this.loadUsers();
  }

  clearFilters(): void {
    this.filterForm.reset({
      search: '',
      role: '',
      is_active: '',
    });
    this.currentPage.set(1);
    this.loadUsers();
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages() || page === this.currentPage()) return;
    this.currentPage.set(page);
    this.loadUsers();
  }

  loadUsers(): void {
    this.loading.set(true);
    this.error.set(null);

    const { search, role, is_active } = this.filterForm.getRawValue();
    this.usersService
      .getUsers({
        search,
        role,
        is_active,
        page: this.currentPage(),
      })
      .subscribe({
        next: (res) => {
          this.users.set(res.results);
          this.totalCount.set(res.count);
          this.loading.set(false);
        },
        error: (err: HttpErrorResponse) => {
          this.error.set(
            this.extractErrorMessage(err, 'No pudimos cargar el listado de usuarios.')
          );
          this.loading.set(false);
        },
      });
  }

  isSelf(user: AdminUser): boolean {
    return this.auth.user()?.id === user.id;
  }

  isProtectedSuperuser(user: AdminUser): boolean {
    return user.is_superuser && !this.currentIsSuperuser();
  }

  isRowDisabled(user: AdminUser): boolean {
    return (
      this.isSelf(user) ||
      this.isProtectedSuperuser(user) ||
      this.updatingUserId() === user.id
    );
  }

  toggleActive(user: AdminUser): void {
    if (this.isRowDisabled(user)) return;

    const nextActive = !user.is_active;
    this.updatingUserId.set(user.id);
    this.actionError.set(null);
    this.actionMessage.set(null);

    this.usersService.updateUser(user.id, { is_active: nextActive }).subscribe({
      next: (updated) => {
        this.replaceUser(updated);
        this.updatingUserId.set(null);
        this.actionMessage.set(
          `Cuenta de ${updated.email} ${updated.is_active ? 'activada' : 'desactivada'}.`
        );
      },
      error: (err: HttpErrorResponse) => {
        this.updatingUserId.set(null);
        this.actionError.set(
          this.extractErrorMessage(err, 'No fue posible actualizar el estado de la cuenta.')
        );
      },
    });
  }

  toggleRole(user: AdminUser): void {
    if (this.isRowDisabled(user)) return;

    const nextRole: 'CLIENTE' | 'ADMIN' = user.role === 'ADMIN' ? 'CLIENTE' : 'ADMIN';
    this.updatingUserId.set(user.id);
    this.actionError.set(null);
    this.actionMessage.set(null);

    this.usersService.updateUser(user.id, { role: nextRole }).subscribe({
      next: (updated) => {
        this.replaceUser(updated);
        this.updatingUserId.set(null);
        this.actionMessage.set(
          `Rol de ${updated.email} actualizado a ${updated.role}.`
        );
      },
      error: (err: HttpErrorResponse) => {
        this.updatingUserId.set(null);
        this.actionError.set(
          this.extractErrorMessage(err, 'No fue posible actualizar el rol del usuario.')
        );
      },
    });
  }

  private resolveSelfSuperuser(): void {
    const authUser = this.auth.user() as (User & { is_superuser?: boolean }) | null;
    if (!authUser || typeof authUser.is_superuser === 'boolean') return;

    this.usersService
      .getUser(authUser.id)
      .pipe(catchError(() => of(null)))
      .subscribe((detail) => {
        if (detail) {
          this.fetchedSelfSuperuser.set(detail.is_superuser);
        }
      });
  }

  private replaceUser(updated: AdminUser): void {
    this.users.update((list) =>
      list.map((item) => (item.id === updated.id ? updated : item))
    );
  }

  private extractErrorMessage(err: HttpErrorResponse, fallback: string): string {
    const body = err.error as Record<string, unknown> | null;
    if (!body) return fallback;
    if (typeof body['detail'] === 'string' && body['detail'].trim()) {
      return body['detail'];
    }
    for (const key of ['is_active', 'role', 'non_field_errors']) {
      const val = body[key];
      if (Array.isArray(val) && typeof val[0] === 'string') {
        return val[0];
      }
    }
    return fallback;
  }
}
