import { Link } from "react-router";

import { Card, buttonVariants } from "../components/ui";
import { PageHeader } from "../components/layout";

export function NotFoundPage() {
  return (
    <div className="mx-auto grid min-h-svh w-full max-w-[42rem] content-center gap-space-4 px-space-4 py-space-8">
      <PageHeader title="Сторінку не знайдено" eyebrow="404" description="Перевірте адресу або поверніться до головної сторінки." />
      <Card className="grid gap-space-4">
        <p className="m-0 text-body text-muted-foreground">Ця адреса не відповідає доступній сторінці.</p>
        <div><Link className={buttonVariants({ variant: "primary", size: "md" })} to="/">На головну</Link></div>
      </Card>
    </div>
  );
}
