import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export const Input = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement>
>(({ className, ...rest }, ref) => (
  <input
    ref={ref}
    className={cn("mira-input px-4 py-[14px] text-[15px]", className)}
    {...rest}
  />
));

Input.displayName = "Input";
