import { describe, it, expect } from 'vitest';
import { cn } from './utils';

describe('cn', () => {
  describe('basic merging', () => {
    it('test_cn_returns_single_class_unchanged', () => {
      expect(cn('p-4')).toBe('p-4');
    });

    it('test_cn_merges_two_non_conflicting_classes', () => {
      expect(cn('p-4', 'mt-2')).toBe('p-4 mt-2');
    });

    it('test_cn_merges_multiple_non_conflicting_classes', () => {
      const result = cn('flex', 'items-center', 'gap-4');
      expect(result).toBe('flex items-center gap-4');
    });

    it('test_cn_returns_empty_string_when_no_args', () => {
      expect(cn()).toBe('');
    });

    it('test_cn_handles_single_empty_string', () => {
      expect(cn('')).toBe('');
    });
  });

  describe('conditional classes (falsy values)', () => {
    it('test_cn_ignores_undefined_values', () => {
      expect(cn('p-4', undefined)).toBe('p-4');
    });

    it('test_cn_ignores_null_values', () => {
      expect(cn('p-4', null)).toBe('p-4');
    });

    it('test_cn_ignores_false_values', () => {
      expect(cn('p-4', false)).toBe('p-4');
    });

    it('test_cn_ignores_zero_value', () => {
      // 0 is falsy — clsx treats it as falsy
      expect(cn('p-4', 0 as unknown as string)).toBe('p-4');
    });

    it('test_cn_handles_conditional_class_that_is_truthy', () => {
      const isActive = true;
      expect(cn('base', isActive && 'active')).toBe('base active');
    });

    it('test_cn_handles_conditional_class_that_is_falsy', () => {
      const isActive = false;
      expect(cn('base', isActive && 'active')).toBe('base');
    });

    it('test_cn_handles_mixed_truthy_and_falsy_conditionals', () => {
      const a = true;
      const b = false;
      const c = true;
      expect(cn(a && 'class-a', b && 'class-b', c && 'class-c')).toBe('class-a class-c');
    });

    it('test_cn_handles_all_falsy_args', () => {
      expect(cn(undefined, null, false)).toBe('');
    });
  });

  describe('tailwind conflict deduplication', () => {
    it('test_cn_deduplicates_conflicting_padding_classes', () => {
      // twMerge resolves conflicts: last one wins
      expect(cn('p-4', 'p-8')).toBe('p-8');
    });

    it('test_cn_deduplicates_conflicting_margin_classes', () => {
      expect(cn('mt-2', 'mt-6')).toBe('mt-6');
    });

    it('test_cn_deduplicates_conflicting_text_size_classes', () => {
      expect(cn('text-sm', 'text-lg')).toBe('text-lg');
    });

    it('test_cn_deduplicates_conflicting_background_color_classes', () => {
      expect(cn('bg-red-500', 'bg-blue-500')).toBe('bg-blue-500');
    });

    it('test_cn_deduplicates_conflicting_width_classes', () => {
      expect(cn('w-4', 'w-full')).toBe('w-full');
    });

    it('test_cn_deduplicates_conflicting_flex_direction_classes', () => {
      expect(cn('flex-row', 'flex-col')).toBe('flex-col');
    });

    it('test_cn_keeps_non_conflicting_classes_alongside_conflict_winner', () => {
      const result = cn('flex', 'p-4', 'p-8', 'mt-2');
      // flex and mt-2 are kept, p-8 wins over p-4
      expect(result).toContain('flex');
      expect(result).toContain('p-8');
      expect(result).toContain('mt-2');
      expect(result).not.toContain('p-4');
    });

    it('test_cn_deduplicates_across_more_than_two_conflicts', () => {
      // Last class wins when multiple same-property classes are provided
      expect(cn('p-2', 'p-4', 'p-8')).toBe('p-8');
    });

    it('test_cn_does_not_remove_non_conflicting_similar_prefix_classes', () => {
      // px- and py- do not conflict with each other
      const result = cn('px-4', 'py-2');
      expect(result).toContain('px-4');
      expect(result).toContain('py-2');
    });
  });

  describe('array and object input (clsx features)', () => {
    it('test_cn_handles_array_of_classes', () => {
      expect(cn(['flex', 'items-center'])).toBe('flex items-center');
    });

    it('test_cn_handles_object_with_truthy_keys', () => {
      expect(cn({ flex: true, hidden: false, 'items-center': true })).toBe('flex items-center');
    });

    it('test_cn_handles_nested_arrays', () => {
      expect(cn(['p-4', ['mt-2', 'ml-2']])).toBe('p-4 mt-2 ml-2');
    });
  });

  describe('edge cases', () => {
    it('test_cn_handles_duplicate_identical_classes', () => {
      // twMerge deduplicates exact duplicates
      expect(cn('flex', 'flex')).toBe('flex');
    });

    it('test_cn_handles_arbitrary_tailwind_values', () => {
      // Arbitrary values like p-[10px] should pass through
      expect(cn('p-[10px]', 'mt-4')).toBe('p-[10px] mt-4');
    });

    it('test_cn_handles_responsive_prefix_classes', () => {
      // md: prefixed classes should not conflict with unprefixed ones
      const result = cn('p-4', 'md:p-8');
      expect(result).toContain('p-4');
      expect(result).toContain('md:p-8');
    });

    it('test_cn_handles_hover_variant_classes', () => {
      const result = cn('text-gray-500', 'hover:text-white');
      expect(result).toContain('text-gray-500');
      expect(result).toContain('hover:text-white');
    });

    it('test_cn_handles_long_class_string', () => {
      const result = cn(
        'flex flex-col items-center justify-center',
        'w-full h-full',
        'bg-white text-black',
      );
      expect(result).toBe('flex flex-col items-center justify-center w-full h-full bg-white text-black');
    });
  });
});
