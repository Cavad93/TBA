import React from 'react';

export interface RadioProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: React.ReactNode;
  description?: React.ReactNode;
}

/**
 * Single-choice control. Give options the same `name` to group them
 * (e.g. shift type: «Полный день» / «Пара часов» / «По ситуации»).
 */
export function Radio(props: RadioProps): React.ReactElement;
