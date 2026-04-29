/**
 * @file components/ui/index.ts
 * @brief Barrel export for design-system primitives.
 */
export { Button, type ButtonProps } from './Button';
export { IconButton, type IconButtonProps } from './IconButton';
export { Input, type InputProps } from './Input';
export { Textarea, type TextareaProps } from './Textarea';
export { Select, Option, type SelectProps } from './Select';
export { Card, type CardProps } from './Card';
export { SettingsRow, type SettingsRowProps } from './SettingsRow';
export { Modal, type ModalProps } from './Modal';
export { Drawer, type DrawerProps } from './Drawer';
export { Tabs, TabList, Tab, TabPanel } from './Tabs';
export { Skeleton, type SkeletonProps } from './Skeleton';
export { EmptyState, type EmptyStateProps } from './EmptyState';
export { Avatar, AvatarGroup, type AvatarProps } from './Avatar';
export { Badge, Chip, type BadgeProps, type ChipProps } from './Badge';
export { ToastRoot } from './Toast';
export { Tooltip, type AppTooltipProps } from './Tooltip';
export { CommandPalette, type CommandItem, type CommandPaletteProps } from './CommandPalette';
export { Markdown, type MarkdownProps } from './Markdown';
export * as motionPrimitives from './motion';
