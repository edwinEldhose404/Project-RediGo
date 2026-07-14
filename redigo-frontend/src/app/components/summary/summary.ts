import { CommonModule, DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize, switchMap } from 'rxjs';

interface Post {
  id: string;
  title: string;
  author: string;
  subreddit: string;
  score: number;
  num_comments: number;
  url: string;
  created_utc: string;
  post_summary: string;
  comments_summary: string;
  comment_agreement_percentage: number;
  comment_disagreement_percentage: number;
  comment_neutral_percentage: number;
}

interface PostsResponse {
  posts: Post[];
  total: number;
  page: number;
  page_size: number;
}

@Component({
  selector: 'app-summary',
  host: { '[class.dark-mode]': 'darkMode' },
  imports: [CommonModule, FormsModule, DatePipe],
  templateUrl: './summary.html',
  styleUrl: './summary.css',
})
export class SummaryComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly changeDetector = inject(ChangeDetectorRef);
  private readonly apiUrl = 'http://localhost:8000/api';

  posts: Post[] = [];
  subreddit = 'worldnews';
  sort = 'hot';
  postLimit = 5;
  darkMode = false;
  currentPage = 1;
  readonly pageSize = 10;
  totalPosts = 0;
  loading = false;
  refreshing = false;
  error = '';
  message = '';

  get totalPages(): number { return Math.max(1, Math.ceil(this.totalPosts / this.pageSize)); }

  get pageNumbers(): number[] { return Array.from({ length: this.totalPages }, (_, index) => index + 1); }

  ngOnInit(): void { this.loadPosts(); }

  loadPosts(): void {
    this.loading = true;
    this.error = '';
    this.http.get<PostsResponse>(`${this.apiUrl}/posts`, {
      params: { page: this.currentPage, limit: this.pageSize },
    }).subscribe({
      next: ({ posts, total, page }) => {
        this.posts = posts;
        this.totalPosts = total;
        this.currentPage = page;
        this.loading = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.error = 'Could not reach the RediGo API. Start the backend on port 8000.';
        this.loading = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  refresh(): void {
    this.refreshing = true;
    this.error = '';
    this.message = '';
    this.http.post<{ processed_count: number }>(`${this.apiUrl}/refresh`, {
      subreddit: this.subreddit.trim(), post_limit: this.postLimit, comment_limit_per_post: 10, sort: this.sort,
    }).pipe(
      switchMap(({ processed_count }) => {
        this.message = processed_count
          ? `Added ${processed_count} new post${processed_count === 1 ? '' : 's'}.`
          : 'No new posts found; showing saved summaries.';
        this.currentPage = 1;
        return this.http.get<PostsResponse>(`${this.apiUrl}/posts`, {
          params: { page: this.currentPage, limit: this.pageSize },
        });
      }),
      finalize(() => {
        this.refreshing = false;
        this.changeDetector.markForCheck();
      }),
    ).subscribe({
      next: ({ posts, total, page }) => {
        this.posts = posts;
        this.totalPosts = total;
        this.currentPage = page;
        this.changeDetector.markForCheck();
      },
      error: (response) => {
        this.error = response.error?.detail || 'Refresh failed. Check the backend logs and API credentials.';
        this.changeDetector.markForCheck();
      },
    });
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages || page === this.currentPage || this.loading || this.refreshing) return;
    this.currentPage = page;
    this.loadPosts();
  }

  toggleDarkMode(): void {
    this.darkMode = !this.darkMode;
  }
}
