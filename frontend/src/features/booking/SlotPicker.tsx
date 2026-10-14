import type { Slot } from "@/api/types";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { formatTime } from "@/lib/format";

type SlotPickerProps = {
  slots: Slot[] | undefined;
  isLoading: boolean;
  selected: string | null;
  onSelect: (slotId: string) => void;
  name: string;
};

/**
 * Native radio inputs styled as pills. Using real radios (visually hidden, not removed) gives
 * arrow-key navigation and correct screen-reader semantics for free; Tailwind's `has-*`
 * variants style the label from the input's state without any JavaScript.
 */
export function SlotPicker({ slots, isLoading, selected, onSelect, name }: SlotPickerProps) {
  if (isLoading) return <Spinner label="Loading free times" />;
  if (!slots?.length) return <Alert>No free times on this day. Try another date.</Alert>;

  return (
    <fieldset>
      <legend className="mb-2 text-sm font-medium text-ink">Free times</legend>
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
        {slots.map((slot) => (
          <label
            key={slot.id}
            className="flex h-10 cursor-pointer items-center justify-center rounded-control border border-line bg-surface text-sm font-medium tabular-nums transition-colors hover:border-brand has-checked:border-brand has-checked:bg-brand has-checked:text-brand-ink has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-focus motion-reduce:transition-none"
          >
            <input
              type="radio"
              name={name}
              value={slot.id}
              checked={selected === slot.id}
              onChange={() => {
                onSelect(slot.id);
              }}
              className="sr-only"
            />
            {formatTime(slot.starts_at)}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
