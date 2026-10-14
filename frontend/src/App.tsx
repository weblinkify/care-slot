import { AppShell } from "@/components/AppShell";
import { Card, CardTitle } from "@/components/ui/Card";

export function App() {
  return (
    <AppShell>
      <Card>
        <CardTitle>Welcome to CareSlot</CardTitle>
        <p className="mt-2 text-sm text-ink-muted">
          Book appointments and manage your data-sharing consent. All data is synthetic.
        </p>
      </Card>
    </AppShell>
  );
}
