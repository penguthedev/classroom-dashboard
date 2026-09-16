import { useEffect, useState } from "react";
import { Bot, X } from "lucide-react";

import { AssistantPanel } from "@/components/assistant/assistant-panel";
import { cn } from "@/lib/utils";

export function AssistantWidget() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key.toLowerCase() === "j" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen((value) => !value);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={open ? "Close assistant" : "Open assistant"}
        aria-expanded={open}
        className={cn(
          "fixed bottom-5 right-5 z-50 flex size-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg",
          "transition-transform hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          open && "sm:right-[calc(420px+1.25rem)] lg:right-[calc(460px+1.25rem)]",
        )}
      >
        {open ? <X className="size-5" /> : <Bot className="size-5" />}
      </button>

      <AssistantPanel open={open} onClose={() => setOpen(false)} />
    </>
  );
}
