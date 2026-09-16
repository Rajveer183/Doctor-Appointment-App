import clsx from 'clsx'

export default function Card({ className, children, hoverable = false, ...props }) {
  return (
    <div
      className={clsx(
        'rounded-xl border border-slate-200 bg-white p-4 shadow-sm',
        hoverable && 'transition-all duration-200 hover:shadow-md hover:-translate-y-0.5',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}
