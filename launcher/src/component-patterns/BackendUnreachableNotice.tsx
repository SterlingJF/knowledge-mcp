// File: launcher/src/component-patterns/BackendUnreachableNotice.tsx

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/component-elements/card'

export type BackendUnreachableNoticeProps = {
  message: string
}

export function BackendUnreachableNotice({
  message,
}: BackendUnreachableNoticeProps) {
  return (
    <Card className="mx-auto mt-16 max-w-xl">
      <CardHeader>
        <CardTitle role="heading" aria-level={1}>
          The backend is not answering
        </CardTitle>
        <CardDescription>{message}</CardDescription>
      </CardHeader>
      <CardContent className="text-muted-foreground text-sm">
        <p>Nothing has been read and nothing has been written.</p>
      </CardContent>
    </Card>
  )
}
