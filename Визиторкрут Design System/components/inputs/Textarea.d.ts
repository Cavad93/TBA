import React from 'react';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: React.ReactNode;
  hint?: React.ReactNode;
  error?: React.ReactNode;
  required?: boolean;
}

/**
 * Multi-line text field for comments to clients, cancellation reasons, etc.
 * Same label/hint/error contract as Input.
 */
export function Textarea(props: TextareaProps): React.ReactElement;
