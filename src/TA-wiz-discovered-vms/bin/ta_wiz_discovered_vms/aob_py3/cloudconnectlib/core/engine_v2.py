#
# Copyright 2024 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import concurrent.futures as cf
import threading
from collections import Iterable
from os import path as op

from ..common.log import get_cc_logger
from .plugin import init_pipeline_plugins

logger = get_cc_logger()


class CloudConnectEngine:
    def __init__(self, max_workers=4, plugin_dir=""):
        """
        Initialize CloudConnectEngine object
        :param max_workers: maximum number of Threads to execute the given calls
        :param plugin_dir: Absolute path of directory containing cce_plugin_*.py
        """
        self._executor = cf.ThreadPoolExecutor(max_workers)
        self._pending_job_results = set()
        self._shutdown = False
        self._pending_jobs = []
        self._counter = 0
        self._lock = threading.RLock()
        plugin_dir = plugin_dir or op.join(op.dirname(op.dirname(__file__)), "plugin")
        init_pipeline_plugins(plugin_dir)

    def start(self, jobs=None):
        """
        Engine starts to run jobs
        :param jobs: A list contains at least one job
        :return:
        """
        try:
            if not jobs:
                logger.warning("CloudConnectEngine just exits with no jobs to run")
                return
            for job in jobs:
                self._add_job(job)
            while not self._shutdown:
                logger.info("CloudConnectEngine starts to run...")
                if not self._pending_job_results:
                    logger.info("CloudConnectEngine has no more jobs to run")
                    break
                # check the intermediate results to find the done jobs and not
                # done jobs
                done_and_not_done_jobs = cf.wait(
                    self._pending_job_results, return_when=cf.FIRST_COMPLETED
                )
                self._pending_job_results = done_and_not_done_jobs.not_done
                done_job_results = done_and_not_done_jobs.done
                for future in done_job_results:
                    # get the result of each done jobs and add new jobs to the
                    # engine if the result spawns more jobs
                    result = future.result()
                    if result:
                        if isinstance(result, Iterable):
                            for temp in result:
                                self._add_job(temp)
                        else:
                            self._add_job(result)
        except Exception:
            logger.exception("CloudConnectEngine encountered exception")
        finally:
            self._teardown()

    def _add_job(self, job):
        """
        add job to engine for scheduling later
        :param job: job should have a 'run' method
        :return:True when the jobs is added successfully and False when the
        engine has shut down
        """
        if self._shutdown:
            return False
        self._pending_jobs.append(job)
        result = self._executor.submit(self._invoke_job, job)
        self._pending_job_results.add(result)
        self._counter += 1
        logger.debug("%s job(s) have been added to the engine now", self._counter)
        return True

    def _invoke_job(self, job):
        """
        Wrap the run method of jobs
        :param job: job should have a 'run' method
        :return:
        """
        try:
            # just return when the engine has shut down
            if self._shutdown:
                return None
            invoke_result = job.run()
            return invoke_result
        except Exception:
            logger.exception("job %s is invoked with exception", job)
            return None
        finally:
            # remove the job from pending_jobs when it's done
            with self._lock:
                self._pending_jobs.remove(job)

    def shutdown(self):
        """
        set the shutdown flag to True
        often called by another thread which needs to shut down
        CloudConnectEngine when e.g. receives a exit signal from external system
        :return:
        """
        self._shutdown = True
        logger.info("CloudConnectEngine receives shutdown signal")

    def _teardown(self):
        """
        internal method which will call stop method of each running jobs
        firstly and then wait for the thread pool to shutdown in a blocked way
        :return:
        """
        logger.info("CloudConnectEngine is going to tear down...")
        self._shutdown = True
        with self._lock:
            for job in self._pending_jobs:
                job.stop()
        self._executor.shutdown(wait=True)
        logger.info("CloudConnectEngine successfully tears down")
