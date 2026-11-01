import { Link } from "react-router";

import { useAuth } from "../app/auth/AuthProvider";
import { Alert, Card, buttonVariants } from "../components/ui";
import { PageHeader } from "../components/layout";

export function HomePage() {
  const { account, notice } = useAuth();
  return (
    <>
      <PageHeader title="Вітаємо у Фітнес-трекері" eyebrow="Особистий простір" description={`Ви увійшли як ${account?.email ?? "користувач"}.`} />
      {notice && <Alert className="mb-space-4" tone="error">{notice}</Alert>}
      <Card className="grid gap-space-3 p-space-6 sm:p-space-8">
        <div className="grid gap-space-2">
          <h2 className="m-0 text-title-medium font-bold text-foreground">Ваш акаунт готовий</h2>
          <p className="m-0 max-w-[42rem] text-body text-muted-foreground">Налаштуйте публічний псевдонім і виберіть, чи показувати вас у рейтингу.</p>
        </div>
        <div>
          <Link className={buttonVariants({ variant: "primary", size: "md" })} to="/settings">Перейти до налаштувань</Link>
        </div>
      </Card>
    </>
  );
}
