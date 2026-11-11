import { Link } from "react-router";

import { useAuth } from "../app/auth/AuthProvider";
import { Alert, Card, buttonVariants } from "../components/ui";
import { PageHeader } from "../components/layout";

const sections = [
  {
    to: "/profile",
    title: "Профіль і вага",
    text: "Стать, вік, вага, зріст і ціль. Історія ваги зберігається автоматично.",
    action: "Відкрити профіль",
  },
  {
    to: "/catalog",
    title: "Бібліотека тренувань",
    text: "Кардіо, силові та йога: готові тренування і окремі вправи.",
    action: "До каталогу",
  },
  {
    to: "/programs",
    title: "Мої програми",
    text: "Отримайте рекомендацію за профілем і налаштуйте склад під себе.",
    action: "До програм",
  },
];

export function HomePage() {
  const { account, notice } = useAuth();
  return (
    <>
      <PageHeader title="Вітаємо у Фітнес-трекері" eyebrow="Особистий простір" description={`Ви увійшли як ${account?.email ?? "користувач"}.`} />
      {notice && <Alert className="mb-space-4" tone="error">{notice}</Alert>}
      <div className="grid gap-space-4 md:grid-cols-3">
        {sections.map((section) => (
          <Card key={section.to} className="grid content-between gap-space-4 p-space-6">
            <div className="grid gap-space-2">
              <h2 className="m-0 text-title-medium font-bold text-foreground">{section.title}</h2>
              <p className="m-0 text-body text-muted-foreground">{section.text}</p>
            </div>
            <div>
              <Link className={buttonVariants({ variant: "primary", size: "md" })} to={section.to}>{section.action}</Link>
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}
