import Image from "next/image";

/** Landing brand lockup: wordmark above the breathing pixel eye. */
export function Wordmark() {
  return (
    <div className="relative mt-16 flex flex-col items-center gap-1">
      <Image
        src="/assets/logo_txt.png"
        alt="mira"
        width={340}
        height={120}
        priority
        className="block w-[min(340px,72vw)] [filter:drop-shadow(0_0_18px_rgba(181,107,255,0.55))]"
      />
      <Image
        src="/assets/logo_eye.png"
        alt=""
        width={340}
        height={200}
        priority
        className="mt-[72px] block w-[min(340px,72vw)] animate-shine [filter:drop-shadow(0_0_16px_rgba(181,107,255,0.5))]"
      />
    </div>
  );
}
