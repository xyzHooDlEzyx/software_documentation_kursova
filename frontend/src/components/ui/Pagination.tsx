import { Button } from "./Button";

export function Pagination({
  page,
  pageSize,
  count,
  onPage,
}: {
  page: number;
  pageSize: number;
  count: number;
  onPage: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (pages <= 1) return null;
  return (
    <nav className="flex items-center justify-between gap-space-3" aria-label="Сторінки">
      <Button variant="outlined" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        Попередня
      </Button>
      <span className="text-small text-muted-foreground">
        Сторінка {page} з {pages}
      </span>
      <Button variant="outlined" size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        Наступна
      </Button>
    </nav>
  );
}
