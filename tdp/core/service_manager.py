import logging
from pathlib import Path
from collections import OrderedDict
from tdp.core.repository.git_repository import GitRepository
from tdp.core.repository.repository import NoVersionYet
from tdp.core.variables import Variables

logger = logging.getLogger("tdp").getChild("git_repository")

SERVICE_NAME_MAX_LENGTH = 15


class ServiceManager:
    def __init__(self, service_name, repository):
        if len(service_name) > SERVICE_NAME_MAX_LENGTH:
            raise ValueError(f"{service_name} is longer than {SERVICE_NAME_MAX_LENGTH}")
        self._name = service_name
        self._repo = repository

    @property
    def name(self):
        return self._name

    @property
    def repository(self):
        return self._repo

    @property
    def version(self):
        return self.repository.current_version()

    @property
    def clean(self):
        return self.repository.is_clean()

    @property
    def path(self):
        return self.repository.path

    def initialize_variables(self, service_default_vars_directory):

        # dict with filepath as key and Path as value
        # a service can have multiple variable files present
        default_var_paths = OrderedDict(
            (path.name, path) for path in service_default_vars_directory.glob("*.yml")
        )

        # If service has no default vars, put a key with a none value
        if not default_var_paths:
            default_var_paths[self.name + ".yml"] = None

        with self.repository.validate(
            f"{self.name}: initial commit"
        ) as repostiory, repostiory.open_var_files(
            default_var_paths.keys()
        ) as configurations:
            # open_var_files returns an OrderedDict, therefore we can iterate over the two values with zip
            for configuration, default_variables_path in zip(
                configurations.values(), default_var_paths.values()
            ):
                if default_variables_path:
                    logger.info(
                        f"Initializing {self.name} with defaults from {service_default_vars_directory}"
                    )
                    with Variables(default_variables_path).open() as variables:
                        configuration.update(variables)
                # service has no default vars
                else:
                    logger.info(f"Initializing {self.name} without variables")
                    pass

    @staticmethod
    def initialize_service_managers(
        services, services_directory, default_vars_directory
    ):
        """get a dict of service managers

        Args:
            services (List[Service]): list of services
            services_directory (PathLike): path of the tdp vars
            default_vars_directory (PathLike): path of the default tdp vars

        Returns:
            Dict[str, ServiceManager]: mapping of service with their manager
        """
        services_directory = Path(services_directory)
        default_vars_directory = Path(default_vars_directory)
        service_managers = {}

        for service in services:
            service_directory = services_directory / service

            try:
                service_directory.mkdir(parents=True)
                logger.info(f"{service_directory.absolute()} does not exist, created")
            except FileExistsError:
                if not service_directory.is_dir():
                    raise ValueError(
                        f"{service_directory.absolute()} should be a directory"
                    )

            repo = GitRepository.init(service_directory)
            service_manager = ServiceManager(service, repo)
            try:
                logger.info(
                    f"{service_manager.name} is already initialized at {service_manager.version}"
                )
            except NoVersionYet:
                service_manager.initialize_variables(default_vars_directory / service)

            service_managers[service] = service_manager

        return service_managers

    @staticmethod
    def get_service_managers(services, services_directory):
        """get a dict of service managers

        Args:
            services (List[Service]): list of services
            services_directory (PathLike): path of the tdp vars

        Returns:
            Dict[str, ServiceManager]: mapping of service with their manager
        """
        services_directory = Path(services_directory)

        service_managers = {}

        for service in services:
            repo = GitRepository(services_directory / service)
            service_managers[service] = ServiceManager(service, repo)

        return service_managers