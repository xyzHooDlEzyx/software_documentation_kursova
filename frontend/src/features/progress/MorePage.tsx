import { Link } from "react-router";
import { PageHeader } from "@/components/layout";
import { Card, buttonVariants } from "@/components/ui";
const links = [
  ["/profile", "Профіль"],
  ["/catalog", "Каталог"],
  ["/settings", "Налаштування"],
  ["/notifications", "Сповіщення"],
] as const;
export function MorePage() {
  return (
    <>
      <PageHeader title="Ще" eyebrow="Розділи" description="Профіль, бібліотека та налаштування застосунку." />
      <div className="grid gap-space-3 sm:grid-cols-2">
        {links.map(([to, label]) => (
          <Card key={to} className="p-space-4">
            <Link className={buttonVariants({ variant: "outlined", className: "w-full" })} to={to}>
              {label}
            </Link>
          </Card>
        ))}
      </div>
    </>
  );
}
