import { HttpErrorResponse } from '@angular/common/http';
import { Component, ElementRef, OnInit, inject, signal, viewChild } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import {
  AdminCatalogService,
  AdminCategory,
} from '../../../core/services/admin-catalog.service';

@Component({
  selector: 'app-admin-categories',
  imports: [ReactiveFormsModule],
  templateUrl: './admin-categories.component.html',
  styleUrl: './admin-categories.component.css',
})
export class AdminCategoriesComponent implements OnInit {
  private readonly adminCatalog = inject(AdminCatalogService);
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly formRef = viewChild<ElementRef<HTMLFormElement>>('categoryFormEl');

  readonly categories = signal<AdminCategory[]>([]);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly deleting = signal(false);
  readonly submitted = signal(false);
  readonly editingId = signal<number | null>(null);
  readonly pendingDelete = signal<AdminCategory | null>(null);
  readonly feedbackMessage = signal<string | null>(null);
  readonly errorMessage = signal<string | null>(null);

  readonly categoryForm = this.fb.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    slug: ['', [Validators.maxLength(110), Validators.pattern(/^[a-z0-9-]*$/)]],
    orden: [0, [Validators.required, Validators.min(0)]],
  });

  ngOnInit(): void {
    this.loadCategories();
  }

  loadCategories(): void {
    this.loading.set(true);
    this.adminCatalog.getCategories().subscribe({
      next: (cats) => {
        this.categories.set(cats);
        this.loading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.loading.set(false);
        this.errorMessage.set(
          err.error?.detail ?? 'No fue posible cargar las categorías.',
        );
      },
    });
  }

  isFieldInvalid(fieldName: 'nombre' | 'slug' | 'orden'): boolean {
    const control = this.categoryForm.controls[fieldName];
    return control.invalid && (control.touched || this.submitted());
  }

  startEdit(category: AdminCategory): void {
    this.editingId.set(category.id);
    this.submitted.set(false);
    this.errorMessage.set(null);
    this.feedbackMessage.set(null);
    this.pendingDelete.set(null);

    this.categoryForm.setValue({
      nombre: category.nombre,
      slug: category.slug,
      orden: category.orden,
    });
  }

  cancelEdit(): void {
    this.editingId.set(null);
    this.submitted.set(false);
    this.categoryForm.reset({ nombre: '', slug: '', orden: 0 });
  }

  submitCategory(): void {
    this.submitted.set(true);
    this.feedbackMessage.set(null);
    this.errorMessage.set(null);

    if (this.categoryForm.invalid) {
      this.categoryForm.markAllAsTouched();
      this.focusFirstInvalid();
      return;
    }

    const raw = this.categoryForm.getRawValue();
    const nombre = raw.nombre.trim();
    const slug = raw.slug.trim();
    const orden = Number(raw.orden);

    if (!nombre) {
      this.categoryForm.controls.nombre.setErrors({ required: true });
      this.focusFirstInvalid();
      return;
    }

    this.saving.set(true);
    const id = this.editingId();
    const payload = {
      nombre,
      orden,
      ...(slug ? { slug } : id !== null ? { slug: '' } : {}),
    };

    const request$ =
      id !== null
        ? this.adminCatalog.updateCategory(id, payload)
        : this.adminCatalog.createCategory(payload);

    request$.subscribe({
      next: (saved) => {
        this.saving.set(false);
        this.feedbackMessage.set(
          id !== null
            ? `Categoría "${saved.nombre}" actualizada.`
            : `Categoría "${saved.nombre}" creada.`,
        );
        this.cancelEdit();
        this.loadCategories();
      },
      error: (err: HttpErrorResponse) => {
        this.saving.set(false);
        this.errorMessage.set(this.extractErrorMessage(err));
      },
    });
  }

  requestDelete(category: AdminCategory): void {
    this.feedbackMessage.set(null);
    this.errorMessage.set(null);
    this.pendingDelete.set(category);
  }

  cancelDelete(): void {
    this.pendingDelete.set(null);
  }

  confirmDelete(): void {
    const target = this.pendingDelete();
    if (!target || this.deleting()) return;

    this.deleting.set(true);
    this.errorMessage.set(null);
    this.feedbackMessage.set(null);

    this.adminCatalog.deleteCategory(target.id).subscribe({
      next: () => {
        this.deleting.set(false);
        this.pendingDelete.set(null);
        if (this.editingId() === target.id) {
          this.cancelEdit();
        }
        this.feedbackMessage.set(`Categoría "${target.nombre}" eliminada.`);
        this.loadCategories();
      },
      error: (err: HttpErrorResponse) => {
        this.deleting.set(false);
        this.pendingDelete.set(null);
        if (err.status === 409) {
          this.errorMessage.set(
            err.error?.detail ??
              `No se puede eliminar "${target.nombre}" porque tiene productos asociados.`,
          );
          return;
        }
        this.errorMessage.set(this.extractErrorMessage(err));
      },
    });
  }

  private focusFirstInvalid(): void {
    const el = this.formRef()?.nativeElement.querySelector<HTMLElement>(
      '[aria-invalid="true"], .ng-invalid',
    );
    el?.focus();
  }

  private extractErrorMessage(err: HttpErrorResponse): string {
    const body = err.error;
    if (!body) return 'No se pudo completar la operación sobre la categoría.';
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.nombre) && body.nombre[0]) return String(body.nombre[0]);
    if (Array.isArray(body.slug) && body.slug[0]) return String(body.slug[0]);
    if (Array.isArray(body.orden) && body.orden[0]) return String(body.orden[0]);
    return 'Verifica los datos ingresados e inténtalo nuevamente.';
  }
}
