import { PersonAvatar as BaseAvatar } from "@/components/eci-files/PersonAvatar";
import type { EciPhoto } from "@/types/eci-files";

/** Phase 5's avatar call sites, on phase 4's component: same photo-or-initials frame, 28px by default. */
export function PersonAvatar({
  name, photo, size = 28, decorative = false,
}: {
  name: string;
  photo?: EciPhoto | null;
  size?: number;
  decorative?: boolean;
}) {
  return <BaseAvatar name={name} photo={photo ?? null} size={size} decorative={decorative} />;
}
