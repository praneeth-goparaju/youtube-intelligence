export interface ThumbnailToDelete {
  channelId: string;
  videoId: string;
  thumbnailStoragePath: string;
}

export async function deleteThumbnailFiles(
  thumbnails: ThumbnailToDelete[],
  deleteFile: (storagePath: string) => Promise<void>
): Promise<{ deleted: ThumbnailToDelete[]; failed: Array<{ thumbnail: ThumbnailToDelete; error: unknown }> }> {
  const deleted: ThumbnailToDelete[] = [];
  const failed: Array<{ thumbnail: ThumbnailToDelete; error: unknown }> = [];
  let nextIndex = 0;

  async function worker(): Promise<void> {
    while (nextIndex < thumbnails.length) {
      const thumbnail = thumbnails[nextIndex++];
      try {
        await deleteFile(thumbnail.thumbnailStoragePath);
        deleted.push(thumbnail);
      } catch (error) {
        if (typeof error === 'object' && error !== null && 'code' in error && error.code === 404) {
          deleted.push(thumbnail);
        } else {
          failed.push({ thumbnail, error });
        }
      }
    }
  }

  await Promise.all(Array.from({ length: Math.min(20, thumbnails.length) }, () => worker()));
  return { deleted, failed };
}
