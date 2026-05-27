import asyncio
import time

from PySide6.QtCore import QObject, Signal

from backend.localization import DeviceLocalizer
from ui.app_state import get_state


class RunController(QObject):
    status_updated = Signal(dict)
    run_finished = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_event = asyncio.Event()
        self._task = None

    def start(self, rsd, gen):
        self._stop_event.clear()
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._run(rsd, gen))

    def stop(self):
        self._stop_event.set()
        if self._task:
            self._task.cancel()

    async def _run(self, rsd, gen):
        state = get_state()
        state.running = True
        t_start = time.time()

        try:
            async with DeviceLocalizer(rsd) as loc:
                state.localizer = loc
                async for data, meta in gen:
                    if self._stop_event.is_set():
                        break
                    if meta is not None:
                        if "done" in meta:
                            self.run_finished.emit(meta)
                            return
                        continue
                    if data is None:
                        continue

                    lat, lng = data[0], data[1]
                    tick = data[2]
                    dist = data[3] if len(data) > 3 and data[3] is not None else 0
                    await loc.set(lat, lng)
                    elapsed = time.time() - t_start
                    self.status_updated.emit({
                        "lat": lat, "lng": lng,
                        "tick": tick, "dist": dist,
                        "elapsed": elapsed,
                    })
                    await asyncio.sleep(0)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            state.running = False
            state.localizer = None
