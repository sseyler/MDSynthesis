"""
The Database object stores information on all Containers it is made aware of.
This centralized storage allows Containers to find each other when necessary;
this is especially important for Groups.

"""
import Core

class Database(Core.Workers.ObjectCore):
    """Database object for tracking and coordinating Containers.

    The Database object stores information on all Containers it is made aware of.
    This centralized storage allows Containers to find each other when necessary;
    this is especially important for Groups.
    
    """
    _containerfile = Core.containerfile
    _databasefile = Core.databasefile
    _containerlog = Core.containerlog

    def __init__(self, database, **kwargs):
        """Generate Database object for the first time, or interface with an existing one.

        :Arguments:
            *database*
                directory containing a Database file; if no Database file is
                found, a new one is generated

        """
        super(Database, self).__init__()
        self.database = dict()              # the database data itself

        database = os.path.abspath(database)
        dbfile = os.path.join(database, self._databasefile)
        if os.path.exists(dbfile):
            self._regenerate(database, **kwargs)
        else:
            self._generate(database, **kwargs)
    
    def _generate(self, database):
        """Generate a new database.
        
        """
        self.database['basedir'] = database
        self._build_metadata()
        self._build_attributes()

        # write to database file
        self.commit()
        self._start_logger(database)

    def _regenerate(self, database):
        """Re-generate existing database.
    
        """
        self.database['basedir'] = database
        self.refresh()
        self._start_logger(database)
        
        self._check_location(database)

        # rebuild missing parts
        self._build_metadata()
        self._build_attributes()

    def _handshake(self):
        """Run check to ensure that database is fine.

        """
        #TODO: add various checks to ensure things are in working order
        return ('basedir' in self.database)

    def search(self, searchstring):
        """Search the Database for Containers that match certain criteria.

        Results are printed in digest form to the screen. To print full
        metadata for all matching containers, use print='full'

        :Arguments:
            *searchstring*
                string giving the search query

        :Keywords:
            *print*
                format of results printed to ouptut

        :Returns:
            *locations*
                filesystem paths to Containers that match criteria

        """
        #TODO: Add in selection system similar to that implemented in
        # MDAnalysis for atom selections. This one, however, will parse
        # metadata elements, and shouldn't be quite so complex

        return

    def add(self, *containers, **kwargs):
        """Add Container to Database.

        :Arguments:
            *containers*
                Containers to add, each given as a path to a Container directory
                or as a generated Container object
            
        """
        for container in containers:
            if isinstance(container, basestring) and os.path.isdir(container):
                with self.util.open(os.path.join(container, self._containerfile), 'r') as f:
                    meta = yaml.load(f)
                uuid = meta['uuid']
                meta['basedir'] = os.path.abspath(container)
                self.database['containers'][uuid] = meta
                with self.util.open(os.path.join(container, self._containerfile), 'w') as f:
                    yaml.dump(meta, f)
            else:
                uuid = container.metadata['uuid']
                self.database['containers'][uuid] = container.metadata

            self.database['containers'][uuid]['database'] = self.database['basedir']

            # since this method is used for Container init, basedir may not
            # be defined in metadata yet
            if not ('basedir' in self.database['containers'][uuid]):
                container.metadata['basedir'] = self._build_basedir(uuid)
                self.database['containers'][uuid]['basedir'] = container.metadata['basedir']
                with self.util.open(os.path.join(container.metadata['basedir'], self._containerfile), 'w') as f:
                    yaml.dump(self.database['containers'][uuid], f)
                self.commit()
            else:
                self.push(uuid)
            self._logger.info("Added {} container '{}' to database.".format(self.database['containers'][uuid]['class'], self.database['containers'][uuid]['name']))

    def remove(self, *containers, **kwargs):
        """Remove Container from Database.

        Note: if Container name is used to specify removal and more than one
        Container has that name, then both will be removed.

        :Arguments:
            *containers*
                Containers to remove, each given as a path to a Container directory,
                a Container UUID, or a Container's given name

        :Keywords:
            *hard*
                if True, delete Container object from filesystem too ``[False]``
            *all*
                if True, will remove all entries ``[False]``
        """
        all_conts = kwargs.pop('all', False)

        if all_conts:
            containers = [ x for x in self.database['containers'] ]

        for container in containers:
            if os.path.isdir(container):
                basedir = os.path.abspath(container)
                contype = ['basedir']
            else:
                contype = ['uuid', 'name']

            matches = []
            for entry in self.database['containers'].values():
                for criteria in contype:
                    if entry[criteria] == container:
                        matches.append(entry['uuid'])
    
            for match in matches:
                self.database['containers'].pop(match, None)

    def clean(self):
        """Clear entries from Database corresponding to Containers that can't be found.

        """
        self._logger.info("Cleaning out entries that cannot be found.")

        uuids = [ x for x in self.database['containers'] ] 
        self._get_containers(*uuids)
        
        for uuid in uuids:
            if not self.database['containers'][uuid]['basedir']:
                self._logger.info("Removing: {} ({})".format(self.database['containers'][uuid]['name'], uuid))
                self.database['containers'].pop(uuid)
        self._logger.info("Database is clean.")

    def commit(self):
        """Save the current state of the database to its file.
        
        """
        self.util.makedirs(self.database['basedir'])
        with self.util.open(os.path.join(self.database['basedir'], self._databasefile), 'w') as f:
            yaml.dump(self.database, f)

    def refresh(self):
        """Reload contents of database file.

        """
        dbfile = os.path.join(self.database['basedir'], self._databasefile)
        with self.util.open(dbfile, 'r') as f:
            self.database = yaml.load(f)

    def pull(self, *containers, **kwargs):
        """Update information stored in Database from Container metadata.

        Note: if Container name is used to specify the update, all Containers
        with that name will be updated in the Database.

        :Arguments:
            *args*
                Containers to update, each given as a path to a Container directory,
                a Container UUID, or a Container's given name

        :Keywords:
            *all*
                if True, will update entries for all known Containers from metadata files
        """
        all_conts = kwargs.pop('all', False)

        if all_conts:
            containers = [ x for x in self.database['containers'] ]
    
        matches = []
        for container in containers:
            if os.path.isdir(container):
                basedir = os.path.abspath(container)
                contype = ['basedir']
            else:
                contype = ['uuid', 'name']

            for entry in self.database['containers'].values():
                for criteria in contype:
                    if entry[criteria] == container:
                        matches.append(entry['uuid'])

        # ensure we are finding the right Container
        basedirs = self._get_containers(*matches)

        for i in xrange(len(matches)):
            if basedirs[i]:
                with self.util.open(os.path.join(basedirs[i], self._containerfile), 'r') as f:
                    self.database['containers'][matches[i]] = yaml.load(f)
        self.commit()

    def push(self, *containers, **kwargs):
        """Update Container metadata with information stored in Database.

        This is the opposite of `:meth:self.pull()`

        Note: if Container name is used to specify the update, all Containers
        with that name will have metadata updated.

        :Arguments:
            *containers*
                Containers to update; either a path to a Container directory,
                Container UUID, or a Container's given name
        :Keywords:
            *all*
                if True, will update all known Container metadata files from entries
        """
        all_conts = kwargs.pop('all', False)

        if all_conts:
            containers = [ x for x in self.database['containers'] ]

        matches = []
        for container in containers:
            if os.path.isdir(container):
                basedir = os.path.abspath(container)
                contype = ['basedir']
            else:
                contype = ['uuid', 'name']

            for entry in self.database['containers'].values():
                for criteria in contype:
                    if entry[criteria] == container:
                        matches.append(entry['uuid'])
    
        # since this method is used for Container init, basedir may not
        # be defined in metadata yet
        for match in matches:
            if not ('basedir' in self.database['containers'][match]):
                self.database['containers'][match]['basedir'] = self._build_basedir(match)
                
        # ensure we are finding the right Container
        basedirs = self._get_containers(*matches)

        for i in xrange(len(matches)):
            if basedirs[i]:
                with self.util.open(os.path.join(basedirs[i], self._containerfile), 'w') as f:
                    yaml.dump(self.database['containers'][matches[i]], f)
        self.commit()

    def _get_containers(self, *uuids):
        """Get path to Containers.

        Will perform checks to ensure the Container returned matches the uuid given.
        It will go looking for the Container if not found at last known location.

        :Arguments:
            *uuids*
                unique ids for Containers to return

        :Returns:
            *containers*
                tuple giving paths to Containers
        """
        containers = [None]*len(uuids)
        missing = [None]*len(uuids)
        for i in xrange(len(uuids)):
            if not self.database['containers'][uuids[i]]['basedir']:
                continue

            if os.path.exists(os.path.join(self.database['containers'][uuids[i]]['basedir'], self._containerfile)):
                with self.util.open(os.path.join(self.database['containers'][uuids[i]]['basedir'], self._containerfile), 'r') as f:
                    meta = yaml.load(f)
                if meta['uuid'] == uuids[i]:
                    containers[i] = self.database['containers'][uuids[i]]['basedir']
                else:
                    self._logger.info("Missing: {} ({})".format(self.database['containers'][uuids[i]]['name'], uuids[i]))
                    missing[i] = uuids[i]
            else:
                self._logger.info("Missing: {} ({})".format(self.database['containers'][uuids[i]]['name'], uuids[i]))
                missing[i] = uuids[i]

        if any(missing):
            missing = self._locate_containers(*missing)

        # build final list of paths
        for i in xrange(len(uuids)):
            if not containers[i]:
                containers[i] = missing[i]

        return containers

    def discover(self):
        """Traverse filesystem downward from Database directory and add all new Containers found.
        
        """
        for root, dirs, files in os.walk(self.database['basedir']):
            if self._containerfile in files:
                dirs = []
                self.add(root)
        self.commit()
    
    def merge(self, database):
        """Merge another database's contents into this one.
        
        :Arguments:
            *database*
                path to database or Database object

        """

    def split(self, database):
        """Split selected Containers off of database into another.
        
        :Arguments:
            *database*
                path to destination database or Database object
        """

    def _check_location(self, database, **kwargs):
        """Check Database location; if changed, send new location to all Containers.

        :Keywords:
            *force*
                if True, new location sent to all Containers even if unchanged;
                default False
        """
        force = kwargs.pop('force', False)
        database = os.path.abspath(database)

        if (database != self.database['basedir']) or force:
            self.database['basedir'] = database

            # update entries first
            self.pull(all=True)

            for entry in self.database['containers'].values():
                entry['database'] = self.database['basedir']
                            
            self.commit()
            self.push(all=True)

    def _build_metadata(self, **kwargs):
        """Build metadata. Runs each time object is generated.
        
        Only adds keys; never modifies existing ones.

        """
        attributes = {'class': self.__class__.__name__,
                      'name': kwargs.pop('name', os.path.basename(self.database['basedir'])),
                      'containers': dict(),
                      }
    
        for key in attributes:
            if not key in self.database:
                self.database[key] = attributes[key]

    def _build_attributes(self):
        """Build attributes of Database. Runs each time object is generated.

        """

    def _locate_containers(self, *uuids):
        """Find Containers by traversing downward through the filesystem. 

        Looks in each directory below the Database. If found, the basedir for the
        Container is updated in both metadata and the Database.

        :Arguments:
            *uuids*
                unique ids for Containers to return
        """
        self._logger.info("Searching for {} Containers.".format(len(uuids) - uuids.count(None)))
        containers = [None]*len(uuids)
        for root, dirs, files in os.walk(self.database['basedir']):
            if self._containerfile in files:
                dirs = []
                with self.util.open(os.path.join(root, self._containerfile), 'r') as f:
                    meta = yaml.load(f)
                try: 
                    i = uuids.index(meta['uuid'])
                    containers[i] = os.path.abspath(root)
                    meta['basedir'] = containers[i]

                    # update basedir in Container metadata and in Database
                    with self.util.open(os.path.join(root, self._containerfile), 'w') as f:
                        yaml.dump(meta, f)
                    self.database['containers'][uuids[i]]['basedir'] = containers[i]
                    self._logger.info("Found: {} ({})\nLocation: {}".format(meta['name'], uuids[i], meta['basedir']))
                except ValueError:
                    pass

        for i in xrange(len(containers)):
            if uuids[i]:
                if not containers[i]:
                    self.database['containers'][uuids[i]]['basedir'] = None
                    self._logger.warning("Not found: {} ({})".format(self.database['containers'][uuids[i]]['name'], uuids[i]))
                    
        self._logger.info("{} Containers not found.".format(containers.count(None) - uuids.count(None)))
        return containers

    def _build_basedir(self, uuid):
        """Build basedir location based on database location, Container class, and Container name.

        :Arguments:
            *database*
                directory where database resides
            *name*
        """
        database = self.database['basedir']
        container = self.database['containers'][uuid]

        # if name given and directory with name doesn't already exist, make named basedir
        if container['name'] and not os.path.exists(os.path.join(database, container['class'], container['name'])):
            dest = container['name']
        # if basedir already exists, use UUID instead
        else:
            dest = container['uuid']

        dest = os.path.join(database, container['class'], dest)
        self.util.makedirs(dest)

        return dest

    def _start_logger(self, basedir):
        """Start up the logger.

        """
        # set up logging
        self._logger = logging.getLogger('{}.{}'.format(self.__class__.__name__, self.database['name']))

        if not self._logger.handlers:
            self._logger.setLevel(logging.INFO)

            # file handler
            logfile = os.path.join(basedir, self._containerlog)
            fh = logging.FileHandler(logfile)
            ff = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
            fh.setFormatter(ff)
            self._logger.addHandler(fh)

            # output handler
            ch = logging.StreamHandler(sys.stdout)
            cf = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
            ch.setFormatter(cf)
            self._logger.addHandler(ch)