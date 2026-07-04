import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...rest }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "mira-input min-h-24 resize-y p-4 text-[15px] leading-[1.5]",
      className
    )}
    {...rest}
  />
));

Textarea.displayName = "Textarea";
